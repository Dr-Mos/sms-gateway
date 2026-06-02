# Webhook Request Template

[中文文档](webhook-template.zh-CN.md)

When an SMS arrives, the gateway turns it into an outgoing HTTP request and sends
it to every enabled webhook. Each webhook stores a **request template** written in
a small, Hurl-inspired plain-text format. This page is the complete reference.

> The format is *inspired by* [Hurl](https://hurl.dev) but is a deliberately small
> subset implemented on top of Python `requests`. It is not a full Hurl runtime —
> there are no response assertions, captures, variables, or filters.

## At a glance

```
METHOD URL
Header-Name: value
[Section]
key: value
request body (verbatim)
```

- **Line 1** — the HTTP method and the URL, separated by a space.
- **Following lines** — request headers, one `Name: value` per line.
- **Optional `[Section]` blocks** — structured extras (query, form, cookies, auth, options).
- **Body** — everything from the first line that no longer looks like a header.

A minimal example:

```
POST https://ntfy.sh/my-topic
Title: SMS from ##FROM##

##CONTENT##
```

## Placeholders

Before the request is sent, these tokens are replaced with values from the incoming SMS:

| Placeholder | Replaced with |
|-------------|---------------|
| `##FROM##` | Sender's phone number |
| `##TO##` | The modem's own number (from the `MODEM_PHONE` setting) |
| `##CONTENT##` | The SMS message text |
| `##FROM_IN_JSON##` | Same as `##FROM##`, but **JSON-escaped** |
| `##TO_IN_JSON##` | Same as `##TO##`, but **JSON-escaped** |
| `##CONTENT_IN_JSON##` | Same as `##CONTENT##`, but **JSON-escaped** |

### When to use the `_IN_JSON` variants

Inside a JSON body, **always** use the `_IN_JSON` form. SMS text often contains
characters that would otherwise break JSON — double quotes, backslashes, or
newlines. The `_IN_JSON` variant escapes them so the body stays valid JSON.

```
POST https://api.day.app/YOUR_KEY/
Content-Type: application/json; charset=utf-8

{"title":"From ##FROM_IN_JSON##","body":"##CONTENT_IN_JSON##","group":"SMS"}
```

If the message were `He said "hi"`, the plain `##CONTENT##` would produce invalid
JSON (`"body":"He said "hi""`), while `##CONTENT_IN_JSON##` produces the correct
`"body":"He said \"hi\""`.

Outside JSON (a plain text body, or a header value), use the plain placeholders.

## The request line

```
METHOD URL
```

`METHOD` is any HTTP verb (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, …). The `URL`
must be a full `http://` or `https://` address. Placeholders may appear in the URL.

## Headers

Each header is a `Name: value` line directly under the request line:

```
POST https://example.com/hook
Content-Type: application/json
Authorization: Bearer my-token
```

Header *values* may contain placeholders. Any newlines in a substituted value are
stripped (so SMS content can never inject extra header lines).

## The body

The body starts at the **first line that no longer looks like a header** — for
example a line beginning with `{`, `[`, or `<`, or any line without a `Name:`
prefix. No blank line is required:

```
POST https://example.com/hook
Content-Type: application/json
{"text":"##CONTENT_IN_JSON##"}
```

You **may** still put a blank line between the head and the body. This is only
necessary when the body's first line would itself look like a header (i.e. it
starts with `something:`):

```
POST https://example.com/hook

Time: ##CONTENT##
```

### Automatic JSON content type

If the body starts with `{` or `[` and you did not set a `Content-Type` header,
`Content-Type: application/json` is added automatically.

## Sections

Sections are optional `[Name]` blocks that add structured parts to the request.
Put them in the head, before the body.

### `[Query]` — URL query parameters

```
GET https://example.com/search
[Query]
q: ##CONTENT##
order: newest
```

### `[Form]` — form-encoded body

Sends `application/x-www-form-urlencoded`. Cannot be combined with a separate body.

```
POST https://example.com/contact
[Form]
from: ##FROM##
text: ##CONTENT##
```

### `[Cookies]` — request cookies

```
GET https://example.com/inbox
[Cookies]
session: abc123
```

### `[BasicAuth]` — HTTP basic authentication

A single `username: password` line.

```
GET https://example.com/private
[BasicAuth]
admin: ##CONTENT##
```

### `[Options]` — per-request options

Only two options are supported:

| Option | Effect |
|--------|--------|
| `insecure: true` | Skip TLS certificate verification (for self-signed HTTPS) |
| `max-time: <seconds>` | Total request timeout (default 15) |

```
POST https://self-signed.lan/hook
[Options]
insecure: true
max-time: 8

##CONTENT##
```

## Validation

The template is checked when you **save** the webhook. If it is malformed —
an unsupported section or option, a missing URL, a header line that is neither a
header nor a recognizable body — the save is rejected with the reason and the
editor stays open so you can fix it.

## What is intentionally not supported

To keep the engine small and safe (incoming SMS is untrusted input), the following
Hurl / curl features are **not** available, and will be reported as an error:

- File bodies and multipart file uploads (`file,…;`, `[Multipart]`)
- Client certificates, proxies, `--unix-socket`, HTTP/3, rate limits
- GraphQL bodies, base64/hex bodies, `{{var}}` filters and functions

If you need one of these, forward to a small relay of your own that does it.

## More examples

**WeCom bot** (note: `\n` inside the JSON string is a literal JSON newline escape):

```
POST https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
Content-Type: application/json

{"msgtype":"text","text":{"content":"SMS\nFrom: ##FROM_IN_JSON##\nText: ##CONTENT_IN_JSON##"}}
```

**DingTalk bot:**

```
POST https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN
Content-Type: application/json

{"msgtype":"text","text":{"content":"SMS\nFrom: ##FROM_IN_JSON##\nText: ##CONTENT_IN_JSON##"}}
```

**Plain GET with the message in the query string:**

```
GET https://example.com/notify
[Query]
from: ##FROM##
msg: ##CONTENT##
```
