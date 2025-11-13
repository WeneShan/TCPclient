#!/bin/bash
# A6 网络丢包环境设置脚本

set -e

# 配置参数
INTERFACE="ens33"  # 网络接口，根据实际情况修改
PACKET_LOSS="10%"  # 默认丢包率

# 显示用法
usage() {
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  -i <接口>    网络接口名称 (默认: $INTERFACE)"
    echo "  -l <丢包率>  丢包百分比 (默认: $PACKET_LOSS)"
    echo "  -h          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -i ens33 -l 15%    # 在ens33接口设置15%丢包"
    echo "  $0                    # 使用默认设置"
}

# 解析命令行参数
while getopts "i:l:h" opt; do
    case $opt in
        i) INTERFACE="$OPTARG" ;;
        l) PACKET_LOSS="$OPTARG" ;;
        h) usage; exit 0 ;;
        *) usage; exit 1 ;;
    esac
done

echo "=== 设置网络丢包环境 ==="
echo "接口: $INTERFACE"
echo "丢包率: $PACKET_LOSS"
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

# 清除现有规则（忽略错误，因为可能没有规则）
echo "清除现有网络规则..."
tc qdisc del dev "$INTERFACE" root 2>/dev/null || true

# 设置丢包
echo "设置 $PACKET_LOSS 丢包率在接口 $INTERFACE 上..."
if tc qdisc add dev "$INTERFACE" root netem loss "$PACKET_LOSS"; then
    echo "✅ 网络丢包设置成功"
else
    echo "❌ 网络丢包设置失败"
    exit 1
fi

# 验证设置
echo ""
echo "当前网络设置:"
tc qdisc show dev "$INTERFACE"

echo ""
echo "✅ 网络丢包环境设置完成"
echo ""
echo "现在可以运行 A6 测试: python3 test/A6/test_A6_corrupt_block.py"
echo ""
echo "测试完成后，运行以下命令清除设置:"
echo "  sudo test/A6/cleanup_packet_loss.sh -i $INTERFACE"
echo ""
echo "或者使用自动化测试脚本:"
echo "  sudo test/A6/run_test_with_packet_loss.sh"