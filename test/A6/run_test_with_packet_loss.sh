#!/bin/bash
# A6 带网络丢包的自动化测试脚本

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
    echo "  $0 -i ens33 -l 15%    # 在ens33接口设置15%丢包并运行测试"
    echo "  $0                    # 使用默认设置运行测试"
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

echo "=== A6 带网络丢包测试开始 ==="
echo "接口: $INTERFACE"
echo "丢包率: $PACKET_LOSS"
echo ""

# 检查当前目录
if [ ! -f "test/A6/test_A6_corrupt_block.py" ]; then
    echo "错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 设置网络丢包
echo "设置网络丢包环境..."
if ! test/A6/setup_packet_loss.sh -i "$INTERFACE" -l "$PACKET_LOSS"; then
    echo "❌ 网络丢包设置失败，退出测试"
    exit 1
fi

# 捕获错误以确保清理
cleanup() {
    echo ""
    echo "正在清理网络环境..."
    test/A6/cleanup_packet_loss.sh -i "$INTERFACE"
}

# 设置陷阱，确保在脚本退出时清理网络
trap cleanup EXIT

# 运行测试
echo ""
echo "执行 A6 测试..."
if python3 test/A6/test_A6_corrupt_block.py; then
    echo "✅ A6 测试完成"
else
    echo "❌ A6 测试失败"
    exit 1
fi

echo ""
echo "=== A6 带网络丢包测试完成 ==="