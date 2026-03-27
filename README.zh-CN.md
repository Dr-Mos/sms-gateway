# SMS Gateway

基于 GSM Modem + Gammu 的短信收发网关，提供 Web 管理界面和 Webhook 转发能力。

适用于 Huawei E3372 等 USB modem，可部署在 Unraid、树莓派或任何 Linux 主机上。

> **关于本项目**：由人类设计、规划并主导开发，代码实现由 [Claude](https://claude.ai)（Anthropic）在人类的持续指导和审查下完成。

## 功能

- **发送短信** — 支持中文等 Unicode 内容，自动处理编码
- **接收短信** — 后台轮询 modem，自动入库，支持长短信（分段短信）自动拼接
- **Webhook 转发** — 收到新短信后通过自定义 curl 模板转发到 Bark、ntfy、企业微信、钉钉等任意平台
- **Webhook 执行日志** — 完整记录每次 webhook 的请求、响应和错误信息
- **Modem 状态** — 通过 AT 命令实时显示信号强度、网络注册状态、运营商、SIM 状态、IMEI
- **密码保护** — 简易登录，密码通过环境变量配置
- **设备热插拔** — ttyUSB 设备可随时插拔，恢复后自动继续工作
- **数据安全** — 指纹去重机制，确保短信不丢失、不重复；数据库分库存储

## 快速开始

### Docker 部署（推荐）

```bash
# 构建镜像
docker build -t sms-gateway .

# 运行
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

访问 `http://<host-ip>:5000`，输入密码登录。

### Docker Compose

```bash
docker-compose up -d --build
```

可创建 `.env` 文件配置参数：

```env
PASSWORD=your-password
SECRET_KEY=a-random-string
MODEM_PHONE=+8613800001111
```

### 本地开发

```bash
pip install -r requirements.txt
PASSWORD=admin POLL_INTERVAL=3 python app.py
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PASSWORD` | `admin` | 登录密码 |
| `TTY_SMS` | `/dev/ttyUSB1` | 短信收发串口（gammu 使用，E3372 通常为 ttyUSB1） |
| `TTY_AT` | 空 | AT 命令查询串口，用于读取信号、运营商等状态（E3372 通常为 `/dev/ttyUSB0`），不设则 Modem 状态页信息不可用 |
| `POLL_INTERVAL` | `3` | 轮询新短信的间隔（秒） |
| `SECRET_KEY` | 自动生成 | Flask session 密钥，不设则每次重启后需重新登录 |
| `MODEM_PHONE` | 空 | Modem 的手机号码，用于 Webhook 模板中的 `##TO##` 占位符 |

## 设备热插拔

Docker 部署时通过 `-v /dev:/dev:ro` 加 `--device-cgroup-rule='c 188:* rmw'` 实现热插拔支持，无需 `--privileged`。`188` 是 Linux 中 ttyUSB 设备的固定主设备号，此配置仅开放 ttyUSB 类设备的访问权限。

设备不在时轮询自动跳过，设备恢复后自动继续工作。

## Webhook 配置

Webhook 使用 curl 命令模板，支持三个占位符：

| 占位符 | 说明 |
|--------|------|
| `##FROM##` | 发送人号码 |
| `##TO##` | 接收端号码（即 modem 号码，取自 `MODEM_PHONE` 环境变量） |
| `##CONTENT##` | 短信内容 |

### 示例模板

**Bark：**

```
curl -X POST "https://api.day.app/YOUR_KEY/" -H "Content-Type: application/json; charset=utf-8" -d '{"body":"##CONTENT##","title":"来自 ##FROM##","group":"SMS"}'
```

**ntfy：**

```
curl -X POST -H "Title: SMS from ##FROM##" -d "##CONTENT##" https://ntfy.sh/YOUR_TOPIC
```

**企业微信机器人：**

```
curl -X POST -H "Content-Type: application/json" -d '{"msgtype":"text","text":{"content":"短信通知\n发送人: ##FROM##\n内容: ##CONTENT##"}}' "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
```

模板支持多行（反斜杠续行）和 bash `$'...'` 引号语法。建议写成单行以避免解析问题。

## 短信处理机制

### 指纹去重

每条短信根据发送号码、发送时间、内容（及分段信息）生成 SHA-256 指纹，数据库中建有唯一索引。重复短信自动跳过，确保：

- 服务重启不会重复导入
- 数据库写入失败时短信不会丢失（下次轮询会重试）
- 首次启动时 modem 中已有的短信会被完整导入

### 长短信拼接

运营商会将超长短信拆分为多个 part 分别发送。系统会：

1. 将每个 part 原样存入数据库，保留原始数据
2. 检测到同一组分段短信的所有 part 齐全后，拼接内容发送一次 Webhook
3. Web 页面自动将同组 part 拼接展示为一条完整短信

### SIM 卡存储管理

SIM 卡短信存储空间有限（通常 50 条），存满后无法接收新短信。系统在轮询时会自动删除已确认写入数据库的短信，释放 SIM 卡空间。

## 数据存储

数据分两个 SQLite 数据库独立存储：

| 文件 | 内容 |
|------|------|
| `data/sms.db` | 收发短信记录 |
| `data/webhooks.db` | Webhook 配置和执行日志 |

分库设计使得修改某一部分的表结构时不影响另一部分的数据。

## API 接口

所有 API 需要先通过 `/api/login` 认证获取 session。

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/login` | 登录，body: `{"password":"xxx"}` |
| POST | `/api/logout` | 退出登录 |

### 短信

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/sms/send` | 发送短信，body: `{"phone":"+86...","text":"内容"}` |
| GET | `/api/sms/list` | 短信列表，参数: `direction`, `page`, `per_page` |

### Webhook

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/webhooks` | 列出所有 webhook |
| POST | `/api/webhooks` | 创建，body: `{"name":"...","curl_template":"..."}` |
| PUT | `/api/webhooks/<id>` | 更新 |
| DELETE | `/api/webhooks/<id>` | 删除（同时删除相关日志） |
| POST | `/api/webhooks/<id>/test` | 发送测试请求 |

### Webhook 日志

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/webhook-logs` | 日志列表，参数: `webhook_id`, `page`, `per_page` |
| POST | `/api/webhook-logs/clear` | 清空日志，body: `{"webhook_id":1}` 或 `{}` 清全部 |

### 设备

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 设备状态、modem 短信数量、轮询间隔 |
| GET | `/api/modem/status` | AT 命令查询：信号强度、网络注册、运营商、SIM 状态、IMEI |

## E3372 部署说明

Huawei E3372 插入 Linux 后默认以 USB 大容量存储模式（产品 ID `14fe`）出现，需要通过 `usb_modeswitch` 切换到 modem 模式（产品 ID `1506`）才会出现 `/dev/ttyUSB*` 设备。

项目仓库中提供了 `e3372-deploy.sh` 部署脚本（针对 Unraid），一键完成：

- udev 规则配置（热插拔自动切换）
- 开机等待切换脚本（开机时设备已插着的场景）
- go 文件自动配置（Unraid 开机自动执行）
- flock 互斥锁（防止并发切换冲突）

```bash
chmod +x e3372-deploy.sh
./e3372-deploy.sh
```

## 项目结构

```
sms-gateway/
├── app.py              # 主应用（Flask + 轮询线程 + API）
├── templates/
│   ├── login.html      # 登录页面
│   └── index.html      # 管理控制台（单页应用）
├── requirements.txt    # Python 依赖
├── Dockerfile
├── docker-compose.yml
├── e3372-deploy.sh     # E3372 Unraid 部署脚本（可选）
└── data/               # 运行时生成
    ├── sms.db
    └── webhooks.db
```

## License

MIT
