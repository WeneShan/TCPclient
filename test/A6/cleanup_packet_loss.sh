#!/bin/bash
# A6 网络丢包环境清理脚本

set -e

# 配置参数
INTERFACE="ens33"  # 网络接口，根据实际情况修改

# 显示用法
usage() {
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  -i <接口>    网络接口名称 (默认: $INTERFACE)"
    echo "  -h          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -i ens33    # 清理ens33接口的网络设置"
    echo "  $0             # 使用默认接口清理"
}

# 解析命令行参数
while getopts "i:h" opt; do
    case $opt in
        i) INTERFACE="$OPTARG" ;;
        h) usage; exit 0 ;;
        *) usage; exit 1 ;;
    esac
done

echo "=== 清理网络丢包设置 ==="
echo "接口: $INTERFACE"
echo ""

# 检查网络接口是否存在
if ! ip link show "$INTERFACE" &>/dev/null; then
    echo "错误: 网络接口 $INTERFACE 不存在"
    echo "可用的接口:"
    ip link show | grep -E "^[0-9]+:" | awk -F: '{print $2}' | tr -d ' '
    exit 1
fi

# 检查tc命令是否可用
if ! command -v tc &>/dev/null; then
    echo "错误: tc 命令未找到，请安装 iproute2 包"
    echo "安装命令: sudo apt update && sudo apt install iproute2"
    exit 1
fi

# 清除规则
echo "清除网络规则..."
if tc qdisc del dev "$INTERFACE" root 2>/dev/null; then
    echo "✅ 网络规则清除成功"
else
    echo "⚠️  没有找到需要清除的网络规则（可能是已经清理过了）"
fi

# 验证清理
echo ""
echo "当前网络设置:"
tc qdisc show dev "$INTERFACE"

echo ""
echo "✅ 网络设置已恢复"
echo ""
echo "网络环境现在恢复正常状态"