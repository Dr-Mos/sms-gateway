#!/bin/bash
# 文件建议保存路径：/boot/custom/deploy-e3372-udev.sh
# 用途：Unraid 下为 Huawei E3372 配置 udev 自动切换到 1506 模式 + 热插拔支持
# 执行一次即可完成所有部署（包括修改 go 文件）
#
# 覆盖场景：
#   1. 脚本执行时 E3372 已插着 → 立即切换
#   2. 设备插着 E3372 开机 → 开机后自动切换（通过 go 文件中的后台等待脚本）
#   3. 运行中热插拔 E3372 → udev 规则自动切换

set -euo pipefail

echo "=== E3372 udev 自动切换部署脚本 开始 ==="

# ─── 0. 检查 usb_modeswitch ───
if ! command -v usb_modeswitch >/dev/null 2>&1; then
    echo ""
    echo "【错误】未找到 usb_modeswitch 命令"
    echo "请通过 un-get 包管理器安装："
    echo "    un-get install usb-modeswitch"
    echo "安装完成后重新运行此脚本"
    echo ""
    exit 1
fi
echo "✓ usb_modeswitch 已存在"

# ─── 1. 创建 udev 规则（处理热插拔场景） ───
mkdir -p /boot/config/udev.rules.d

cat > /boot/config/udev.rules.d/40-e3372.rules << 'UDEV_EOF'
# E3372 插入时如果是 14fe（HiLink/存储模式），自动切换到 1506（modem模式）
# 使用 flock 避免与开机等待脚本同时执行 usb_modeswitch 产生冲突
# 使用 & 后台执行避免阻塞 udev 事件队列
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="12d1", ATTR{idProduct}=="14fe", RUN+="/bin/bash -c 'flock -n /tmp/e3372-switch.lock -c \"/usr/sbin/usb_modeswitch -v 12d1 -p 14fe -V 12d1 -P 1506 -M 55534243123456780000000000000011060000000000000000000000000000\" &'"
UDEV_EOF

echo "✓ udev 规则文件已写入：/boot/config/udev.rules.d/40-e3372.rules"

# ─── 2. 创建开机等待切换脚本（处理开机时设备已插着的场景） ───
mkdir -p /boot/custom
cat > /boot/custom/e3372-boot-switch.sh << 'BOOT_EOF'
#!/bin/bash
# 开机时后台运行：等待 E3372 被内核枚举，然后执行模式切换
# 设备上电到被识别为 14fe 可能需要 5~30 秒
#
# 与 udev 规则共享 flock 锁，避免同时执行 usb_modeswitch

LOG_TAG="e3372-boot"
LOCK_FILE="/tmp/e3372-switch.lock"
MAX_WAIT=60
INTERVAL=3
WAITED=0

logger -t "$LOG_TAG" "开机切换脚本启动，等待 E3372 设备..."

while [ $WAITED -lt $MAX_WAIT ]; do
    # 已经是 1506 → 不管是谁切的，任务完成
    if lsusb 2>/dev/null | grep -q "12d1:1506"; then
        logger -t "$LOG_TAG" "E3372 已处于 1506 modem 模式，无需切换"
        exit 0
    fi

    # 检测到 14fe → 尝试拿锁切换
    if lsusb 2>/dev/null | grep -q "12d1:14fe"; then
        logger -t "$LOG_TAG" "检测到 14fe，尝试获取锁执行切换..."

        (
            # flock -w 30: 等锁最多 30 秒，拿不到就放弃
            flock -w 30 200 || { logger -t "$LOG_TAG" "获取锁超时，放弃"; exit 1; }

            # 拿到锁后再检查一次：可能 udev 那边已经切好了
            if lsusb 2>/dev/null | grep -q "12d1:1506"; then
                logger -t "$LOG_TAG" "获取锁后发现已是 1506，无需切换"
                exit 0
            fi

            if ! lsusb 2>/dev/null | grep -q "12d1:14fe"; then
                logger -t "$LOG_TAG" "获取锁后 14fe 已消失，可能正在切换中"
                exit 0
            fi

            logger -t "$LOG_TAG" "持锁执行 usb_modeswitch..."
            /usr/sbin/usb_modeswitch -v 12d1 -p 14fe -V 12d1 -P 1506 \
                -M "55534243123456780000000000000011060000000000000000000000000000" \
                2>&1 | logger -t "$LOG_TAG"

        ) 200>"$LOCK_FILE"

        # 等设备重新枚举
        sleep 5
        if lsusb 2>/dev/null | grep -q "12d1:1506"; then
            logger -t "$LOG_TAG" "切换成功，E3372 已进入 1506 modem 模式"
        else
            logger -t "$LOG_TAG" "切换后未检测到 1506，可能需要更长时间"
        fi
        exit 0
    fi

    sleep $INTERVAL
    WAITED=$((WAITED + INTERVAL))
done

logger -t "$LOG_TAG" "等待超时（${MAX_WAIT}秒），未检测到 E3372 设备"
exit 0
BOOT_EOF

chmod +x /boot/custom/e3372-boot-switch.sh
echo "✓ 开机等待脚本已写入：/boot/custom/e3372-boot-switch.sh"

# ─── 3. 修改 go 文件 ───
GO_FILE="/boot/config/go"
MARKER_START="# === E3372 自动切换开始 ==="
MARKER_END="# === E3372 自动切换结束 ==="

# 如果已存在旧配置，先删掉（幂等更新）
if grep -qF "$MARKER_START" "$GO_FILE" 2>/dev/null; then
    echo "检测到旧的 E3372 配置段，先移除..."
    sed -i "/$MARKER_START/,/$MARKER_END/d" "$GO_FILE"
    # 清理可能残留的空行
    sed -i '/^$/N;/^\n$/d' "$GO_FILE"
fi

cat >> "$GO_FILE" << EOF

$MARKER_START
# 复制 udev 规则并加载（处理热插拔）
mkdir -p /etc/udev/rules.d
cp -f /boot/config/udev.rules.d/40-e3372.rules /etc/udev/rules.d/40-e3372.rules
udevadm control --reload-rules

# 后台启动等待脚本（处理开机时设备已插着的情况）
# udev 规则只在 add 事件时触发，开机时设备可能已经完成枚举
# 所以需要额外脚本轮询检测并切换
nohup /boot/custom/e3372-boot-switch.sh >/dev/null 2>&1 &
$MARKER_END
EOF

echo "✓ go 文件已更新"

# ─── 4. 立即生效 ───
# 复制规则并重新加载
mkdir -p /etc/udev/rules.d
cp -f /boot/config/udev.rules.d/40-e3372.rules /etc/udev/rules.d/40-e3372.rules
udevadm control --reload-rules
udevadm trigger --subsystem-match=usb --action=add
echo "✓ udev 规则已加载"

# 如果当前是 14fe，立即切换
if lsusb | grep -q "12d1:14fe"; then
    echo "检测到 14fe 模式，正在切换到 1506..."
    /usr/sbin/usb_modeswitch -v 12d1 -p 14fe -V 12d1 -P 1506 \
        -M "55534243123456780000000000000011060000000000000000000000000000"
    sleep 6
    if lsusb | grep -q "12d1:1506"; then
        echo "✓ 切换成功"
    else
        echo "⚠ 切换后未立即检测到 1506，请稍等几秒后检查"
    fi
elif lsusb | grep -q "12d1:1506"; then
    echo "✓ E3372 已经处于 1506 modem 模式"
else
    echo "ℹ 未检测到 E3372 设备"
fi

# ─── 5. 最终状态 ───
echo ""
echo "=== 部署完成 ==="
echo "Huawei USB 设备："
lsusb | grep -i huawei || echo "  （未检测到）"
echo "ttyUSB 设备："
ls -la /dev/ttyUSB* 2>/dev/null || echo "  （未检测到）"
echo ""
echo "部署内容："
echo "  /boot/config/udev.rules.d/40-e3372.rules  — udev 规则（热插拔自动切换）"
echo "  /boot/custom/e3372-boot-switch.sh          — 开机等待切换脚本"
echo "  /boot/config/go                            — 已追加开机自动执行配置"
echo ""
echo "验证建议："
echo "  1. 热插拔一次 E3372，检查是否自动出现 ttyUSB 设备"
echo "  2. 重启 Unraid，检查开机后 E3372 是否自动切换"
echo "  3. 查看日志：grep e3372-boot /var/log/syslog"
