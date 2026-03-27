# SMS Gateway

An SMS send/receive gateway based on GSM Modem + Gammu, with a web management interface and webhook forwarding.

Compatible with Huawei E3372 and similar USB modems. Deployable on Unraid, Raspberry Pi, or any Linux host.

> **About this project**: Designed, planned, and led by a human; code implemented by [Claude](https://claude.ai) (Anthropic) under continuous human guidance and review.

[中文文档](README.zh-CN.md)

## Features

- **Send SMS** — Unicode support (Chinese, Japanese, etc.) with automatic encoding handling
- **Receive SMS** — Background polling of modem, auto-stored to database, automatic reassembly of multi-part messages
- **Webhook forwarding** — Forward incoming SMS to Bark, ntfy, WeCom, DingTalk, or any platform via custom curl templates
- **Webhook logs** — Full record of every webhook request, response, and error
- **Modem status** — Real-time signal strength, network registration, operator, SIM status, and IMEI via AT commands
- **Password protection** — Simple login with password configured via environment variable
- **Hot-plug support** — ttyUSB devices can be connected/disconnected at any time; polling resumes automatically
- **Data integrity** — SHA-256 fingerprint deduplication ensures no messages are lost or duplicated; separate databases for SMS and webhooks

## Quick Start

### Docker (recommended)

```bash
# Build image
docker build -t sms-gateway .

# Run
docker run -d \
  --name sms-gateway \
  --restart unless-stopped \
  -p 5000:5000 \
  -v /path/to/data:/data \
  -v /dev:/dev:ro \
  --device-cgroup-rule='c 188:* rmw' \
  -e PASSWORD=your-password \
  sms-gateway
```

Open `http://<host-ip>:5000` and log in with your password.

### Docker Compose

```bash
docker-compose up -d --build
```

Create a `.env` file to configure parameters:

```env
PASSWORD=your-password
SECRET_KEY=a-random-string
MODEM_PHONE=+8613800001111
```

### Local Development

```bash
pip install -r requirements.txt
PASSWORD=admin POLL_INTERVAL=3 python app.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PASSWORD` | `admin` | Login password |
| `TTY_SMS` | `/dev/ttyUSB1` | SMS serial port used by gammu (E3372 is typically ttyUSB1) |
| `TTY_AT` | *(empty)* | AT command serial port for signal/operator status queries (E3372 is typically `/dev/ttyUSB0`); Modem status page is unavailable if not set |
| `POLL_INTERVAL` | `3` | SMS polling interval in seconds |
| `SECRET_KEY` | *(auto-generated)* | Flask session key; if not set, users must re-login after each restart |
| `MODEM_PHONE` | *(empty)* | Modem's phone number, used as `##TO##` placeholder in webhook templates |

## Hot-Plug Support

Docker deployment uses `-v /dev:/dev:ro` combined with `--device-cgroup-rule='c 188:* rmw'` for hot-plug support without requiring `--privileged`. `188` is the fixed major device number for ttyUSB devices in Linux; this configuration grants access only to ttyUSB-class devices.

When the device is absent, polling is automatically skipped and resumes when the device reconnects.

## Webhook Configuration

Webhooks use curl command templates with three placeholders:

| Placeholder | Description |
|-------------|-------------|
| `##FROM##` | Sender's phone number |
| `##TO##` | Recipient number (the modem's own number, from `MODEM_PHONE`) |
| `##CONTENT##` | SMS message content |

### Example Templates

**Bark:**

```
curl -X POST "https://api.day.app/YOUR_KEY/" -H "Content-Type: application/json; charset=utf-8" -d '{"body":"##CONTENT##","title":"From ##FROM##","group":"SMS"}'
```

**ntfy:**

```
curl -X POST -H "Title: SMS from ##FROM##" -d "##CONTENT##" https://ntfy.sh/YOUR_TOPIC
```

**WeCom Bot:**

```
curl -X POST -H "Content-Type: application/json" -d '{"msgtype":"text","text":{"content":"SMS\nFrom: ##FROM##\nContent: ##CONTENT##"}}' "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
```

Templates support multi-line (backslash continuation) and bash `$'...'` quoting. Single-line is recommended to avoid parsing issues.

## SMS Processing

### Fingerprint Deduplication

Each message generates a SHA-256 fingerprint from sender number, timestamp, content, and part information, with a unique index in the database. Duplicates are silently skipped, ensuring:

- No re-import on service restart
- No message loss on database write failure (retried on next poll)
- Full import of messages already on the modem at first start

### Multi-Part SMS Reassembly

Carriers split long messages into multiple parts sent separately. The system:

1. Stores each part as-is in the database, preserving raw data
2. Detects when all parts of a group are complete, then assembles and sends a single webhook
3. Displays all parts of a group as one complete message in the web UI

### SIM Storage Management

SIM card storage is limited (typically 50 messages); new messages cannot be received when full. The system automatically deletes messages confirmed as written to the database during each poll cycle, freeing SIM storage.

## Data Storage

Data is stored in two independent SQLite databases:

| File | Contents |
|------|----------|
| `data/sms.db` | Sent and received SMS records |
| `data/webhooks.db` | Webhook configurations and execution logs |

The split design means changes to one schema do not affect data in the other.

## API Reference

All API endpoints require authentication via `/api/login` first.

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/login` | Login, body: `{"password":"xxx"}` |
| POST | `/api/logout` | Logout |

### SMS

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/sms/send` | Send SMS, body: `{"phone":"+1...","text":"content"}` |
| GET | `/api/sms/list` | List messages, params: `direction`, `page`, `per_page` |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/webhooks` | List all webhooks |
| POST | `/api/webhooks` | Create, body: `{"name":"...","curl_template":"..."}` |
| PUT | `/api/webhooks/<id>` | Update |
| DELETE | `/api/webhooks/<id>` | Delete (also removes related logs) |
| POST | `/api/webhooks/<id>/test` | Send a test request |

### Webhook Logs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/webhook-logs` | List logs, params: `webhook_id`, `page`, `per_page` |
| POST | `/api/webhook-logs/clear` | Clear logs, body: `{"webhook_id":1}` or `{}` for all |

### Device

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/status` | Device status, modem SMS count, poll interval |
| GET | `/api/modem/status` | AT command query: signal, network registration, operator, SIM status, IMEI |

## E3372 Setup

When plugged into Linux, the Huawei E3372 defaults to USB mass storage mode (product ID `14fe`). `usb_modeswitch` must switch it to modem mode (product ID `1506`) before `/dev/ttyUSB*` devices appear.

The repository includes `e3372-deploy.sh` (targeting Unraid) which automates:

- udev rule configuration (automatic mode-switch on hot-plug)
- Boot wait script (for devices already connected at boot)
- go file configuration (Unraid auto-run on boot)
- flock mutex (prevents concurrent mode-switch conflicts)

```bash
chmod +x e3372-deploy.sh
./e3372-deploy.sh
```

## Project Structure

```
sms-gateway/
├── app.py              # Main application (Flask + polling thread + API)
├── templates/
│   ├── login.html      # Login page
│   └── index.html      # Admin console (single-page app)
├── requirements.txt    # Python dependencies
├── Dockerfile
├── docker-compose.yml
├── e3372-deploy.sh     # E3372 Unraid setup script (optional)
└── data/               # Generated at runtime
    ├── sms.db
    └── webhooks.db
```

## License

MIT
