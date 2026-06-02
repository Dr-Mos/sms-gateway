# Webhook 请求模板

[English](webhook-template.md)

收到短信后，网关会把它转换成一个 HTTP 请求，发送给每一个已启用的 webhook。每个
webhook 保存一份**请求模板**，用一种简洁的、受 Hurl 启发的纯文本格式编写。本页是
完整参考。

> 该格式**借鉴**自 [Hurl](https://hurl.dev)，但只是一个基于 Python `requests`
> 实现的精简子集，并非完整的 Hurl 运行时——没有响应断言、捕获、变量或过滤器。

## 速览

```
METHOD URL
Header-Name: value
[Section]
key: value
请求体（逐字原样）
```

- **第 1 行** — HTTP 方法和 URL，用空格分隔。
- **随后各行** — 请求头，每行一个 `名称: 值`。
- **可选的 `[Section]` 区块** — 结构化的附加项（查询参数、表单、cookie、认证、选项）。
- **请求体** — 从第一行"不再像请求头"的行开始的全部内容。

最小示例：

```
POST https://ntfy.sh/my-topic
Title: SMS from ##FROM##

##CONTENT##
```

## 占位符

请求发送前，下列标记会被替换为收到的短信中的值：

| 占位符 | 替换为 |
|--------|--------|
| `##FROM##` | 发送人号码 |
| `##TO##` | Modem 自己的号码（取自 `MODEM_PHONE` 配置） |
| `##CONTENT##` | 短信正文 |
| `##FROM_IN_JSON##` | 同 `##FROM##`，但做 **JSON 转义** |
| `##TO_IN_JSON##` | 同 `##TO##`，但做 **JSON 转义** |
| `##CONTENT_IN_JSON##` | 同 `##CONTENT##`，但做 **JSON 转义** |

### 何时使用 `_IN_JSON` 变体

在 JSON 请求体里**一律**用 `_IN_JSON` 形式。短信内容经常含有会破坏 JSON 的字符——
双引号、反斜杠、换行。`_IN_JSON` 变体会把它们转义，使请求体保持合法 JSON。

```
POST https://api.day.app/YOUR_KEY/
Content-Type: application/json; charset=utf-8

{"title":"来自 ##FROM_IN_JSON##","body":"##CONTENT_IN_JSON##","group":"SMS"}
```

若短信是 `He said "hi"`，普通的 `##CONTENT##` 会生成非法 JSON
（`"body":"He said "hi""`），而 `##CONTENT_IN_JSON##` 会生成正确的
`"body":"He said \"hi\""`。

在 JSON 之外（纯文本请求体、或请求头的值里），用不带 `_IN_JSON` 的普通占位符即可。

## 请求行

```
METHOD URL
```

`METHOD` 是任意 HTTP 动词（`GET`、`POST`、`PUT`、`DELETE`、`PATCH`……）。`URL`
必须是完整的 `http://` 或 `https://` 地址。URL 里也可以使用占位符。

## 请求头

每个请求头是请求行下方的一行 `名称: 值`：

```
POST https://example.com/hook
Content-Type: application/json
Authorization: Bearer my-token
```

请求头的**值**里可以含占位符。被替换进来的值中的换行会被去除（因此短信内容无法注入
额外的请求头行）。

## 请求体

请求体从**第一行"不再像请求头"的行**开始——例如以 `{`、`[`、`<` 开头的行，或任何
没有 `名称:` 前缀的行。**不需要**空行：

```
POST https://example.com/hook
Content-Type: application/json
{"text":"##CONTENT_IN_JSON##"}
```

你**也可以**在头部和请求体之间放一个空行。仅当请求体首行本身长得像请求头时
（即以 `某词:` 开头）才需要这样：

```
POST https://example.com/hook

Time: ##CONTENT##
```

### 自动 JSON 内容类型

若请求体以 `{` 或 `[` 开头、且你没有设置 `Content-Type` 头，会自动补上
`Content-Type: application/json`。

## 小节（Sections）

小节是可选的 `[名称]` 区块，为请求添加结构化部分。请放在头部、请求体之前。

### `[Query]` — URL 查询参数

```
GET https://example.com/search
[Query]
q: ##CONTENT##
order: newest
```

### `[Form]` — 表单编码请求体

发送 `application/x-www-form-urlencoded`。不能与单独的请求体同时使用。

```
POST https://example.com/contact
[Form]
from: ##FROM##
text: ##CONTENT##
```

### `[Cookies]` — 请求 Cookie

```
GET https://example.com/inbox
[Cookies]
session: abc123
```

### `[BasicAuth]` — HTTP 基本认证

单独一行 `用户名: 密码`。

```
GET https://example.com/private
[BasicAuth]
admin: ##CONTENT##
```

### `[Options]` — 单次请求选项

仅支持两个选项：

| 选项 | 作用 |
|------|------|
| `insecure: true` | 跳过 TLS 证书校验（用于自签名 HTTPS） |
| `max-time: <秒>` | 请求总超时（默认 15） |

```
POST https://self-signed.lan/hook
[Options]
insecure: true
max-time: 8

##CONTENT##
```

## 校验

模板在你**保存** webhook 时被检查。若格式有误——不支持的小节或选项、缺少 URL、
某一行既不是请求头也不是可识别的请求体——保存会被拒绝并给出原因，编辑窗口保持
打开以便你修改。

## 有意不支持的功能

为保持引擎精简、安全（收到的短信是不可信输入），以下 Hurl / curl 功能**不**提供，
遇到时会报错：

- 文件请求体与 multipart 文件上传（`file,…;`、`[Multipart]`）
- 客户端证书、代理、`--unix-socket`、HTTP/3、限速
- GraphQL 请求体、base64/hex 请求体、`{{var}}` 过滤器与函数

如确需其中某项，请自建一个小型中继来完成。

## 更多示例

**企业微信机器人**（注意：JSON 字符串里的 `\n` 是 JSON 的换行转义字面量）：

```
POST https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
Content-Type: application/json

{"msgtype":"text","text":{"content":"短信通知\n发送人: ##FROM_IN_JSON##\n内容: ##CONTENT_IN_JSON##"}}
```

**钉钉机器人：**

```
POST https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN
Content-Type: application/json

{"msgtype":"text","text":{"content":"短信通知\n发送人: ##FROM_IN_JSON##\n内容: ##CONTENT_IN_JSON##"}}
```

**用查询字符串携带消息的普通 GET：**

```
GET https://example.com/notify
[Query]
from: ##FROM##
msg: ##CONTENT##
```
