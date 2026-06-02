#!/usr/bin/env python3
"""
SMS Gateway Web Application
Controls a GSM modem (e.g. Huawei E3372) via gammu CLI through ttyUSB.
Provides web UI for sending/receiving SMS and webhook forwarding.

Database split:
  - data/sms.db      : messages (incoming + outgoing SMS)
  - data/webhooks.db : webhook configs + execution logs
"""

import os
import re
import json
import time
import hashlib
import secrets
import logging
import sqlite3
import subprocess
import threading
from datetime import datetime, timezone
from functools import wraps

try:
    import serial
    _serial_available = True
except ImportError:
    _serial_available = False

import requests as http_requests
from flask import (
    Flask, request, jsonify, render_template, redirect,
    url_for, session, g
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

SMS_DB = "/data/sms.db"
WEBHOOK_DB = "/data/webhooks.db"

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "3"))
TTY_SMS = os.environ.get("TTY_SMS", "/dev/ttyUSB1")
TTY_AT = os.environ.get("TTY_AT", "")
GAMMU_CONFIG = "/etc/gammurc"
MODEM_PHONE = os.environ.get("MODEM_PHONE", "")
PASSWORD = os.environ.get("PASSWORD", "admin")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("sms-gateway")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------------------------------------------------------------------------
# Database init
# ---------------------------------------------------------------------------

def init_databases():
    os.makedirs("/data", exist_ok=True)

    conn = _connect(SMS_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            direction     TEXT NOT NULL,
            phone         TEXT NOT NULL,
            content       TEXT NOT NULL,
            status        TEXT DEFAULT 'ok',
            fingerprint   TEXT DEFAULT '',
            concat_id     TEXT DEFAULT '',
            concat_part   INTEGER DEFAULT 0,
            concat_total  INTEGER DEFAULT 0,
            webhook_sent  INTEGER DEFAULT 0,
            raw_meta      TEXT DEFAULT '',
            created_at    TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_fp
            ON messages(fingerprint) WHERE fingerprint != '';
        CREATE INDEX IF NOT EXISTS idx_msg_dir ON messages(direction);
        CREATE INDEX IF NOT EXISTS idx_msg_created ON messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_msg_concat ON messages(concat_id)
            WHERE concat_id != '';
    """)
    conn.close()

    conn = _connect(WEBHOOK_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS webhooks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            curl_template  TEXT NOT NULL DEFAULT '',
            enabled        INTEGER DEFAULT 1,
            created_at     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS webhook_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id      INTEGER NOT NULL,
            webhook_name    TEXT NOT NULL,
            trigger_type    TEXT NOT NULL DEFAULT 'sms',
            sms_phone       TEXT DEFAULT '',
            sms_content     TEXT DEFAULT '',
            request_method  TEXT DEFAULT '',
            request_url     TEXT DEFAULT '',
            request_headers TEXT DEFAULT '',
            request_body    TEXT DEFAULT '',
            response_status INTEGER DEFAULT 0,
            response_body   TEXT DEFAULT '',
            success         INTEGER DEFAULT 0,
            error_message   TEXT DEFAULT '',
            executed_at     TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_whl_wid ON webhook_logs(webhook_id);
        CREATE INDEX IF NOT EXISTS idx_whl_time ON webhook_logs(executed_at);
    """)
    conn.close()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Gammu / modem helpers
# ---------------------------------------------------------------------------

# All gammu operations share this lock to prevent concurrent serial port access
_modem_lock = threading.Lock()
# AT command port lock (independent of gammu)
_at_lock = threading.Lock()


def is_device_available():
    return os.path.exists(TTY_SMS)


def ensure_gammu_config():
    if os.path.exists(GAMMU_CONFIG):
        return
    cfg = f"[gammu]\ndevice = {TTY_SMS}\nconnection = at\n"
    os.makedirs(os.path.dirname(GAMMU_CONFIG) or ".", exist_ok=True)
    with open(GAMMU_CONFIG, "w") as f:
        f.write(cfg)
    log.info("Wrote gammu config to %s", GAMMU_CONFIG)


def _has_non_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def send_sms(phone: str, text: str) -> dict:
    if not is_device_available():
        return {"success": False, "error": f"Device {TTY_SMS} not available"}
    ensure_gammu_config()
    cmd = ["gammu", "-c", GAMMU_CONFIG, "sendsms", "TEXT", phone]
    if _has_non_ascii(text):
        cmd.append("-unicode")
    log.info("Sending SMS to %s (unicode=%s)", phone, _has_non_ascii(text))
    with _modem_lock:
        try:
            proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0:
                log.info("SMS sent successfully to %s", phone)
                return {"success": True, "output": proc.stdout.strip()}
            else:
                log.error("gammu sendsms failed: %s", proc.stderr.strip())
                return {"success": False, "error": proc.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "gammu command timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "gammu binary not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def fetch_all_sms() -> list:
    """Fetch ALL SMS from modem (both read and unread)."""
    if not is_device_available():
        return []
    ensure_gammu_config()
    with _modem_lock:
        try:
            proc = subprocess.run(
                ["gammu", "-c", GAMMU_CONFIG, "getallsms"],
                capture_output=True, text=True, timeout=60,
            )
            if proc.returncode != 0:
                output = proc.stdout + proc.stderr
                if "Error opening device" in output:
                    log.info("gammu: device busy or unavailable (%s)", proc.stdout.strip())
                else:
                    log.warning("gammu getallsms failed (rc=%d): %s",
                                proc.returncode, (proc.stdout + proc.stderr).strip())
                return []
        except Exception as e:
            log.warning("Failed to run gammu getallsms: %s", e)
            return []
    return _parse_gammu_output(proc.stdout)


def _parse_gammu_output(output: str) -> list:
    """
    Parse gammu getallsms output.

    Gammu output format per message:
        Location N, folder "Inbox", SIM memory, Inbox folder
        SMS message
        Key                  : Value
        Key                  : Value
        ...
        <empty line>
        <message body>
        <empty line or EOF>

    Header keys include: SMSC number, Sent, Coding, Remote number,
    Status, User Data Header, etc.
    """
    messages = []
    blocks = re.split(r"(?=Location \d+)", output)

    for block in blocks:
        if not block.strip():
            continue
        if not re.match(r"Location \d+", block.strip()):
            continue

        lines = block.split("\n")

        # Parse the Location line
        loc_m = re.match(r"Location (\d+)", lines[0])
        if not loc_m:
            continue
        location = loc_m.group(1)

        # Skip non-inbox
        first_line = lines[0].lower()
        if "folder" in first_line and "inbox" not in first_line:
            continue

        # Walk through lines: collect headers, then body after first empty line
        headers = {}
        body_start = None

        for i, line in enumerate(lines):
            if i == 0:
                continue  # Location line, already parsed
            if line.strip() == "SMS message":
                continue  # Type indicator, skip

            # Header line: "Key                  : Value"
            header_m = re.match(r"^(\S[\w\s]*?)\s*:\s*(.+)$", line)
            if header_m and body_start is None:
                headers[header_m.group(1).strip()] = header_m.group(2).strip()
                continue

            # Empty line after headers = body starts on next line
            if line.strip() == "" and body_start is None and headers:
                body_start = i + 1
                continue

            # If we haven't found headers yet and line is not a header, skip
            # (handles "SMS message" or other preamble lines)

        # Extract required fields from headers
        phone = headers.get("Remote number", "").strip('"')
        sent = headers.get("Sent", "")
        status = headers.get("Status", "").lower()

        if not phone or not sent:
            continue

        # Parse concatenated SMS info from User Data Header
        concat_id = ""
        concat_part = 0
        concat_total = 0
        udh = headers.get("User Data Header", "")
        if udh:
            concat_m = re.search(
                r"Concatenated.*?ID.*?\)\s*(\d+),\s*part\s*(\d+)\s*of\s*(\d+)", udh
            )
            if concat_m:
                concat_id = concat_m.group(1)
                concat_part = int(concat_m.group(2))
                concat_total = int(concat_m.group(3))

        # Extract body: from body_start to end of block
        body = ""
        if body_start is not None and body_start < len(lines):
            body_lines = lines[body_start:]
            body = "\n".join(body_lines).strip()

        # Remove gammu summary line from last block
        body = re.sub(r"\n?\d+ SMS parts? in \d+ SMS sequences?\s*$", "", body).strip()

        messages.append({
            "location": location, "phone": phone,
            "sent_time": sent, "content": body,
            "status": status,
            "concat_id": concat_id,
            "concat_part": concat_part,
            "concat_total": concat_total,
        })
    return messages


def sms_fingerprint(phone: str, sent_time: str, content: str,
                    concat_id: str = "", concat_part: int = 0) -> str:
    """
    Generate a SHA-256 fingerprint for an SMS message.
    For concatenated SMS, include concat_id and part number to ensure
    each part is unique even if content happens to match.
    """
    raw = f"{phone.strip()}|{sent_time.strip()}|{content.strip()}"
    if concat_id:
        raw += f"|{concat_id}|{concat_part}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def delete_sms(location: str):
    """Delete a specific SMS from modem by location."""
    if not is_device_available():
        return
    ensure_gammu_config()
    with _modem_lock:
        try:
            subprocess.run(
                ["gammu", "-c", GAMMU_CONFIG, "deletesms", "1", location],
                capture_output=True, text=True, timeout=30,
            )
        except Exception as e:
            log.warning("Failed to delete SMS at location %s: %s", location, e)



# ---------------------------------------------------------------------------
# AT command helpers
# ---------------------------------------------------------------------------

def get_modem_status() -> dict:
    """Query modem status via AT commands. Opens serial port once for all queries."""
    if not _serial_available or not TTY_AT or not os.path.exists(TTY_AT):
        return {"available": False}

    def _query(ser, command):
        """Send one AT command on an already-open serial port, return response text."""
        try:
            ser.reset_input_buffer()
            time.sleep(0.05)
            ser.write((command + "\r\n").encode())
            lines = []
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                line = ser.readline()
                if line:
                    lines.append(line)
                    combined = b"".join(lines)
                    if b"OK\r\n" in combined or b"ERROR" in combined:
                        break
                else:
                    break  # readline timed out
            resp = b"".join(lines).decode("utf-8", errors="replace").strip()
            log.info("AT %s → %s", command, resp.replace("\r\n", " ") if resp else "(empty)")
            return resp
        except Exception as e:
            log.warning("AT %s → error: %s", command, e)
            return ""

    result = {"available": True}
    with _at_lock:
        try:
            with serial.Serial(TTY_AT, baudrate=115200, timeout=1) as ser:
                csq = _query(ser, "AT+CSQ")
                m = re.search(r"\+CSQ:\s*(\d+),", csq)
                if m:
                    n = int(m.group(1))
                    result["signal_raw"] = n
                    result["signal_dbm"] = (-113 + n * 2) if n < 99 else None
                    result["signal_pct"] = min(100, int((n / 31) * 100)) if n < 99 else 0

                creg = _query(ser, "AT+CREG?")
                m = re.search(r"\+CREG:\s*\d+,(\d+)", creg)
                if m:
                    stat = int(m.group(1))
                    reg_map = {0: "not_registered", 1: "registered_home",
                               2: "searching", 3: "rejected", 5: "registered_roaming"}
                    result["network_stat"] = stat
                    result["network_status"] = reg_map.get(stat, "unknown")
                    result["network_registered"] = stat in (1, 5)

                cops = _query(ser, "AT+COPS?")
                m = re.search(r'\+COPS:\s*\d+,\d+,"([^"]+)"', cops)
                result["operator"] = m.group(1) if m else ""

                cpin = _query(ser, "AT+CPIN?")
                m = re.search(r"\+CPIN:\s*(\S+)", cpin)
                result["sim_status"] = m.group(1) if m else ""
                result["sim_ready"] = result["sim_status"] == "READY"

                cgsn = _query(ser, "AT+CGSN")
                m = re.search(r"(\d{15})", cgsn)
                result["imei"] = m.group(1) if m else ""

        except Exception as e:
            log.warning("AT port open failed: %s", e)
            return {"available": False}

    return result


# ---------------------------------------------------------------------------
# HTTP request template engine (Hurl-style)
# ---------------------------------------------------------------------------

def _substitute_template(template: str, from_phone: str, to_phone: str, content: str) -> str:
    # JSON-escaped variants: escape the value as a JSON string but keep the
    # template's own surrounding quotes (so `"##CONTENT_IN_JSON##"` stays valid JSON
    # even when the SMS contains ", \, or newlines). Replace these before the
    # plain placeholders so the longer token wins.
    def js(v):
        return json.dumps(v, ensure_ascii=False)[1:-1]
    result = template.replace("##FROM_IN_JSON##", js(from_phone))
    result = result.replace("##TO_IN_JSON##", js(to_phone))
    result = result.replace("##CONTENT_IN_JSON##", js(content))
    result = result.replace("##FROM##", from_phone)
    result = result.replace("##TO##", to_phone)
    result = result.replace("##CONTENT##", content)
    return result


_HURL_SECTIONS = {"query", "form", "cookies", "basicauth", "options"}
_HTTP_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}
# A line is a header / section key-value when it starts with a valid token name
# followed by ':'. JSON/XML/raw body lines (starting with { [ < or any line
# without a 'name:' prefix) don't match, so the body is detected without needing
# a blank-line separator. A section marker is [Word]; a JSON array body like
# [1,2] starts with a digit/quote and is therefore not mistaken for a section.
_HURL_HEADER_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+:")
_HURL_SECTION_RE = re.compile(r"^\[[A-Za-z][\w-]*\]$")


def _parse_hurl(template: str) -> dict:
    """Parse a minimal Hurl-style request definition into a request spec.

    Layout:
        METHOD URL
        Header-Name: value
        [Query] / [Form] / [Cookies] / [BasicAuth] / [Options]
        key: value
        request body (verbatim)

    The body begins at the first line that no longer looks like a header or a
    section (e.g. a `{...}` JSON object, or any line without a `name:` prefix).
    A blank line may also separate the head from the body — handy when the body's
    first line would itself look like a header.

    Placeholders (##CONTENT## etc.) are left untouched here; substitution happens
    after parsing so SMS values can never alter the request structure. Returns a
    spec dict, or {"error": ...} for a malformed template.
    """
    lines = [ln.rstrip("\r") for ln in template.split("\n")]
    n = len(lines)

    # Request line = first non-empty line.
    i = 0
    while i < n and not lines[i].strip():
        i += 1
    if i >= n:
        return {"error": "Empty request template"}
    bits = lines[i].strip().split(None, 1)
    if len(bits) < 2:
        return {"error": f"First line must be 'METHOD URL', got: {lines[i].strip()!r}"}
    method, url = bits[0].upper(), bits[1].strip()
    if method not in _HTTP_METHODS:
        return {"error": f"Unknown HTTP method {bits[0]!r}; the first line must be 'METHOD URL'"}
    if not re.match(r"https?://", url, re.IGNORECASE):
        return {"error": "URL must start with http:// or https://"}
    i += 1

    headers, params, cookies = {}, {}, {}
    form, auth = None, None
    verify, timeout = True, 15
    section = None
    body_start = None
    while i < n:
        s = lines[i].strip()
        if s == "":
            # Blank line: explicit head/body separator.
            body_start = i + 1
            break
        if _HURL_SECTION_RE.match(s):
            section = s[1:-1].strip().lower()
            if section not in _HURL_SECTIONS:
                return {"error": f"Unsupported section [{s[1:-1]}]"}
            if section == "form":
                form = {}
            i += 1
            continue
        if not _HURL_HEADER_RE.match(s):
            # No longer a header/section line -> the body starts here.
            body_start = i
            break
        k, v = s.split(":", 1)
        k, v = k.strip(), v.strip()
        if section is None:
            headers[k] = v
        elif section == "query":
            params[k] = v
        elif section == "form":
            form[k] = v
        elif section == "cookies":
            cookies[k] = v
        elif section == "basicauth":
            auth = [k, v]
        elif section == "options":
            kl = k.lower()
            if kl == "insecure":
                verify = v.lower() not in ("true", "1", "yes", "on")
            elif kl in ("max-time", "connect-timeout"):
                try:
                    timeout = max(1, int(float(v)))
                except ValueError:
                    return {"error": f"Invalid {k} value: {v!r}"}
            else:
                return {"error": f"Unsupported option: {k}"}
        i += 1

    body = None
    if body_start is not None and body_start < n:
        rest = "\n".join(lines[body_start:]).strip("\n")
        body = rest if rest.strip() else None

    if form is not None and body is not None:
        return {"error": "[Form] cannot be combined with a request body"}

    # Default to application/json for a bare JSON body when no Content-Type given.
    auto_json = (
        body is not None and form is None
        and not any(h.lower() == "content-type" for h in headers)
        and body.lstrip()[:1] in ("{", "[")
    )

    return {
        "method": method, "url": url, "headers": headers,
        "params": params, "form": form, "body": body,
        "cookies": cookies, "auth": auth,
        "verify": verify, "timeout": timeout, "auto_json": auto_json,
    }


def _validate_request_template(template: str) -> str:
    """Return an error message if the template is malformed, else ''."""
    return _parse_hurl(template).get("error", "")


def _execute_request_template(template: str, from_phone: str, to_phone: str, content: str) -> dict:
    spec = _parse_hurl(template)
    if "error" in spec:
        return {
            "success": False, "error": spec["error"],
            "request_method": "", "request_url": "",
            "request_headers": "", "request_body": "",
            "response_status": 0, "response_body": "",
        }

    def sub(s):
        return _substitute_template(s, from_phone, to_phone, content)

    def sub_header(s):
        # Strip CR/LF so an SMS value can't inject extra header lines.
        return sub(s).replace("\r", " ").replace("\n", " ")

    method = spec["method"]
    url = sub(spec["url"])
    headers = {sub_header(k): sub_header(v) for k, v in spec["headers"].items()}
    params = {sub(k): sub(v) for k, v in spec["params"].items()} or None
    cookies = {sub(k): sub(v) for k, v in spec["cookies"].items()} or None
    auth = tuple(sub(x) for x in spec["auth"]) if spec["auth"] else None
    form = {sub(k): sub(v) for k, v in spec["form"].items()} if spec["form"] is not None else None
    body = sub(spec["body"]) if spec["body"] is not None else None
    if spec["auto_json"] and body is not None:
        headers.setdefault("Content-Type", "application/json")

    if form is not None:
        data = form
        body_log = "&".join(f"{k}={v}" for k, v in form.items())
    else:
        data = body.encode("utf-8") if body is not None else None
        body_log = body or ""

    result = {
        "request_method": method, "request_url": url,
        "request_headers": json.dumps(headers, ensure_ascii=False) if headers else "",
        "request_body": body_log,
    }

    try:
        resp = http_requests.request(
            method=method, url=url,
            headers=headers or None, params=params, data=data,
            cookies=cookies, auth=auth,
            verify=spec["verify"], timeout=spec["timeout"],
        )
        result.update({
            "success": True, "response_status": resp.status_code,
            "response_body": resp.text[:2000], "error": "",
        })
    except Exception as e:
        result.update({
            "success": False, "response_status": 0,
            "response_body": "", "error": str(e),
        })
    return result


# ---------------------------------------------------------------------------
# Webhook forwarding with logging
# ---------------------------------------------------------------------------

def _log_webhook_execution(webhook_id, webhook_name, trigger_type,
                           sms_phone, sms_content, result):
    try:
        conn = _connect(WEBHOOK_DB)
        conn.execute(
            """INSERT INTO webhook_logs
               (webhook_id,webhook_name,trigger_type,sms_phone,sms_content,
                request_method,request_url,request_headers,request_body,
                response_status,response_body,success,error_message,executed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (webhook_id, webhook_name, trigger_type, sms_phone, sms_content,
             result.get("request_method", ""), result.get("request_url", ""),
             result.get("request_headers", ""), result.get("request_body", ""),
             result.get("response_status", 0), result.get("response_body", ""),
             1 if result.get("success") else 0, result.get("error", ""), utcnow()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("Failed to log webhook execution: %s", e)


def forward_to_webhooks(message_dict: dict):
    conn = _connect(WEBHOOK_DB)
    hooks = conn.execute("SELECT * FROM webhooks WHERE enabled=1").fetchall()
    conn.close()

    from_phone = message_dict.get("phone", "")
    to_phone = MODEM_PHONE or message_dict.get("to", "")
    content = message_dict.get("content", "")

    for hook in hooks:
        template = hook["curl_template"]
        if not template.strip():
            continue
        result = _execute_request_template(template, from_phone, to_phone, content)
        _log_webhook_execution(hook["id"], hook["name"], "sms",
                               from_phone, content, result)
        if result["success"]:
            log.info("Webhook '%s' OK, status=%s", hook["name"], result.get("response_status"))
        else:
            log.error("Webhook '%s' failed: %s", hook["name"], result.get("error"))


# ---------------------------------------------------------------------------
# SMS polling background thread
# ---------------------------------------------------------------------------

class SMSPoller(threading.Thread):
    """
    Polling strategy:
    1. Read ALL SMS from modem (both read and unread)
    2. Each part stored as-is with fingerprint dedup (INSERT OR IGNORE)
    3. For non-concatenated SMS: send webhook immediately, mark webhook_sent=1
    4. For concatenated SMS: check if all parts are in DB;
       if complete and webhook_sent=0, assemble and send webhook, mark all parts
    5. Delete from modem only messages confirmed in DB (fingerprint exists)
    """
    def __init__(self, interval=15):
        super().__init__(daemon=True)
        self.interval = interval
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        log.info("SMS poller started (interval=%ds)", self.interval)
        while not self._stop_event.is_set():
            try:
                self._poll()
            except Exception as e:
                log.error("Poller error: %s", e)
            self._stop_event.wait(self.interval)

    def _poll(self):
        if not is_device_available():
            return
        all_msgs = fetch_all_sms()
        if not all_msgs:
            return

        conn = _connect(SMS_DB)
        new_count = 0
        new_concat_ids = set()

        # Phase 1: Store all messages, track what's new
        for msg in all_msgs:
            fp = sms_fingerprint(
                msg["phone"], msg["sent_time"], msg["content"],
                msg["concat_id"], msg["concat_part"],
            )
            now = utcnow()

            cur = conn.execute(
                "INSERT OR IGNORE INTO messages"
                "(direction,phone,content,status,fingerprint,"
                "concat_id,concat_part,concat_total,webhook_sent,"
                "raw_meta,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,0,?,?)",
                ("incoming", msg["phone"], msg["content"], "ok", fp,
                 msg["concat_id"], msg["concat_part"], msg["concat_total"],
                 json.dumps({"sent_time": msg["sent_time"],
                             "location": msg["location"],
                             "modem_status": msg.get("status", "")}),
                 now),
            )

            if cur.rowcount > 0:
                new_count += 1
                if msg["concat_id"]:
                    new_concat_ids.add(msg["concat_id"])
                else:
                    # Non-concatenated: send webhook immediately
                    conn.execute(
                        "UPDATE messages SET webhook_sent=1 WHERE fingerprint=?",
                        (fp,),
                    )
                    conn.commit()
                    forward_to_webhooks({
                        "phone": msg["phone"], "content": msg["content"],
                        "received_at": now, "modem_sent_time": msg["sent_time"],
                    })

        # Phase 2: Check completeness for concatenated messages
        for cid in new_concat_ids:
            row = conn.execute(
                "SELECT concat_total, COUNT(*) as have FROM messages "
                "WHERE concat_id=? AND direction='incoming'",
                (cid,),
            ).fetchone()

            if not row or row["concat_total"] == 0:
                continue

            if row["have"] >= row["concat_total"]:
                # Check if webhook already sent for this group
                unsent = conn.execute(
                    "SELECT COUNT(*) as c FROM messages "
                    "WHERE concat_id=? AND direction='incoming' AND webhook_sent=0",
                    (cid,),
                ).fetchone()
                if unsent["c"] == 0:
                    continue  # Already sent

                # All parts present — assemble and send
                parts = conn.execute(
                    "SELECT * FROM messages "
                    "WHERE concat_id=? AND direction='incoming' "
                    "ORDER BY concat_part",
                    (cid,),
                ).fetchall()

                combined_content = "".join(p["content"] for p in parts)
                phone = parts[0]["phone"]
                sent_time = json.loads(parts[0]["raw_meta"]).get("sent_time", "")

                # Mark all parts as webhook_sent
                conn.execute(
                    "UPDATE messages SET webhook_sent=1 "
                    "WHERE concat_id=? AND direction='incoming'",
                    (cid,),
                )
                conn.commit()

                forward_to_webhooks({
                    "phone": phone, "content": combined_content,
                    "received_at": utcnow(), "modem_sent_time": sent_time,
                })

        conn.commit()

        # Phase 3: Delete from modem messages that are confirmed in DB
        for msg in all_msgs:
            fp = sms_fingerprint(
                msg["phone"], msg["sent_time"], msg["content"],
                msg["concat_id"], msg["concat_part"],
            )
            exists = conn.execute(
                "SELECT id FROM messages WHERE fingerprint=?", (fp,)
            ).fetchone()
            if exists:
                delete_sms(msg["location"])

        conn.close()

        if new_count:
            log.info("Polled %d SMS from modem, %d new", len(all_msgs), new_count)


# ---------------------------------------------------------------------------
# Routes: Auth
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET"])
def login_page():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    if data.get("password", "") == PASSWORD:
        session["authenticated"] = True
        session.permanent = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "wrong_password"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Routes: Pages
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Routes: SMS API
# ---------------------------------------------------------------------------

@app.route("/api/sms/send", methods=["POST"])
@login_required
def api_send_sms():
    data = request.get_json(force=True)
    phone = data.get("phone", "").strip()
    text = data.get("text", "").strip()
    if not phone or not text:
        return jsonify({"ok": False, "error": "phone_and_content_required"}), 400
    result = send_sms(phone, text)
    conn = _connect(SMS_DB)
    now = utcnow()
    conn.execute(
        "INSERT INTO messages(direction,phone,content,status,fingerprint,"
        "concat_id,concat_part,concat_total,webhook_sent,raw_meta,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("outgoing", phone, text, "ok" if result["success"] else "failed",
         sms_fingerprint(phone, now, text),
         "", 0, 0, 1,
         json.dumps(result), now),
    )
    conn.commit()
    conn.close()
    if result["success"]:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": result.get("error", "send_failed")}), 500


@app.route("/api/sms/list", methods=["GET"])
@login_required
def api_list_sms():
    direction = request.args.get("direction", "")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 50))))
    offset = (page - 1) * per_page
    conn = _connect(SMS_DB)
    where, params = "", []
    if direction in ("incoming", "outgoing"):
        where = "WHERE direction=?"
        params.append(direction)

    total = conn.execute(
        f"SELECT COUNT(*) c FROM messages {where}", params
    ).fetchone()["c"]

    rows = conn.execute(
        f"SELECT * FROM messages {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    # Merge concatenated messages for display
    merged = []
    seen_concat = set()
    for r in rows:
        d = dict(r)
        cid = d.get("concat_id", "")
        if cid:
            if cid in seen_concat:
                continue
            seen_concat.add(cid)
            # Fetch all parts of this concat group
            parts = conn.execute(
                "SELECT content, concat_part FROM messages "
                "WHERE concat_id=? AND direction=? ORDER BY concat_part",
                (cid, d["direction"]),
            ).fetchall()
            d["content"] = "".join(p["content"] for p in parts)
            d["concat_parts_have"] = len(parts)
        merged.append(d)

    conn.close()
    return jsonify({"ok": True, "total": total, "page": page,
                     "per_page": per_page, "messages": merged})


# ---------------------------------------------------------------------------
# Routes: Webhook API
# ---------------------------------------------------------------------------

@app.route("/api/webhooks", methods=["GET"])
@login_required
def api_list_webhooks():
    conn = _connect(WEBHOOK_DB)
    rows = conn.execute("SELECT * FROM webhooks ORDER BY id").fetchall()
    conn.close()
    return jsonify({"ok": True, "webhooks": [dict(r) for r in rows]})


@app.route("/api/webhooks", methods=["POST"])
@login_required
def api_create_webhook():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    curl_template = data.get("curl_template", "").strip()
    if not name or not curl_template:
        return jsonify({"ok": False, "error": "名称和模板不能为空"}), 400
    err = _validate_request_template(curl_template)
    if err:
        return jsonify({"ok": False, "error": err}), 400
    conn = _connect(WEBHOOK_DB)
    conn.execute("INSERT INTO webhooks(name,curl_template,enabled,created_at) VALUES(?,?,1,?)",
                 (name, curl_template, utcnow()))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/webhooks/<int:wid>", methods=["PUT"])
@login_required
def api_update_webhook(wid):
    data = request.get_json(force=True)
    if "curl_template" in data:
        err = _validate_request_template(data["curl_template"].strip())
        if err:
            return jsonify({"ok": False, "error": err}), 400
    conn = _connect(WEBHOOK_DB)
    fields, params = [], []
    for key in ("name", "curl_template"):
        if key in data:
            fields.append(f"{key}=?")
            params.append(data[key].strip())
    if "enabled" in data:
        fields.append("enabled=?")
        params.append(1 if data["enabled"] else 0)
    if not fields:
        conn.close()
        return jsonify({"ok": False, "error": "no_fields_to_update"}), 400
    params.append(wid)
    conn.execute(f"UPDATE webhooks SET {','.join(fields)} WHERE id=?", params)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/webhooks/<int:wid>", methods=["DELETE"])
@login_required
def api_delete_webhook(wid):
    conn = _connect(WEBHOOK_DB)
    conn.execute("DELETE FROM webhooks WHERE id=?", (wid,))
    conn.execute("DELETE FROM webhook_logs WHERE webhook_id=?", (wid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/webhooks/<int:wid>/test", methods=["POST"])
@login_required
def api_test_webhook(wid):
    conn = _connect(WEBHOOK_DB)
    hook = conn.execute("SELECT * FROM webhooks WHERE id=?", (wid,)).fetchone()
    conn.close()
    if not hook:
        return jsonify({"ok": False, "error": "Webhook不存在"}), 404
    result = _execute_request_template(
        hook["curl_template"], "+8613800138000", MODEM_PHONE,
        "这是一条测试短信 / This is a test SMS",
    )
    _log_webhook_execution(wid, hook["name"], "test",
                           "+8613800138000", "这是一条测试短信 / This is a test SMS", result)
    if result["success"]:
        return jsonify({"ok": True, "status_code": result["response_status"],
                         "body": result.get("response_body", "")})
    return jsonify({"ok": False, "error": result["error"]}), 500


# ---------------------------------------------------------------------------
# Routes: Webhook Logs API
# ---------------------------------------------------------------------------

@app.route("/api/webhook-logs", methods=["GET"])
@login_required
def api_list_webhook_logs():
    webhook_id = request.args.get("webhook_id", "")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 30))))
    offset = (page - 1) * per_page
    conn = _connect(WEBHOOK_DB)
    where, params = "", []
    if webhook_id:
        where = "WHERE webhook_id=?"
        params.append(int(webhook_id))
    total = conn.execute(f"SELECT COUNT(*) c FROM webhook_logs {where}", params).fetchone()["c"]
    rows = conn.execute(
        f"SELECT * FROM webhook_logs {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "total": total, "page": page,
                     "per_page": per_page, "logs": [dict(r) for r in rows]})


@app.route("/api/webhook-logs/clear", methods=["POST"])
@login_required
def api_clear_webhook_logs():
    data = request.get_json(force=True) if request.data else {}
    webhook_id = data.get("webhook_id")
    conn = _connect(WEBHOOK_DB)
    if webhook_id:
        conn.execute("DELETE FROM webhook_logs WHERE webhook_id=?", (int(webhook_id),))
    else:
        conn.execute("DELETE FROM webhook_logs")
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Routes: Status API
# ---------------------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
@login_required
def api_status():
    modem_count = None
    if is_device_available():
        msgs = fetch_all_sms()
        modem_count = len(msgs) if msgs is not None else None
    return jsonify({
        "ok": True, "device": TTY_SMS,
        "device_available": is_device_available(),
        "poll_interval": POLL_INTERVAL,
        "modem_sms_count": modem_count,
    })



@app.route("/api/modem/status", methods=["GET"])
@login_required
def api_modem_at_status():
    return jsonify(get_modem_status())


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

init_databases()
ensure_gammu_config()

_flask_debug = os.environ.get("FLASK_DEBUG", "0") in ("1", "true")
_in_reloader_parent = os.environ.get("WERKZEUG_RUN_MAIN") is None and _flask_debug
if not _in_reloader_parent:
    poller = SMSPoller(interval=POLL_INTERVAL)
    poller.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=_flask_debug)
