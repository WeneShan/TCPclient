#!/bin/bash
# STEP 协议虚拟机测试脚本
# 在客户端虚拟机中运行所有测试

set -e  # 遇到错误立即退出

echo "=== STEP 协议虚拟机测试开始 ==="
echo "开始时间: $(date)"
echo ""

# 检查必要文件是否存在
if [ ! -f "vm_test_utils.py" ]; then
    echo "错误: 找不到 vm_test_utils.py"
    exit 1
fi

# 检查服务器连通性
echo "检查服务器连通性..."
python3 -c "
import sys
sys.path.append('.')
from vm_test_utils import VMNetworkTester, VMTestLogger

logger = VMTestLogger('VM_Connectivity_Check')
tester = VMNetworkTester(logger)

if tester.check_server_connectivity():
    print('✓ 服务器连接正常')
else:
    print('✗ 服务器连接失败，请检查服务器是否运行')
    sys.exit(1)
"

echo ""
echo "=== 执行功能性测试 A1-A6 ==="

# A1 基线测试
echo "执行 A1 基线测试..."
python3 A1/test_A1_baseline.py
echo "A1 测试完成"

# A2 极小文件测试
echo "执行 A2 极小文件测试..."
python3 A2/test_A2_edge_files.py
echo "A2 测试完成"

# A3 尾块测试
echo "执行 A3 尾块测试..."
python3 A3/test_A3_tail_block.py
echo "A3 测试完成"

# A4 重复上传测试
echo "执行 A4 重复上传测试..."
python3 A4/test_A4_repeat_upload.py
echo "A4 测试完成"

# A5 认证错误测试
echo "执行 A5 认证错误测试..."
python3 A5/test_A5_auth_error.py
echo "A5 测试完成"

# A6 块损坏测试
echo "执行 A6 块损坏测试..."
python3 A6/test_A6_corrupt_block.py
echo "A6 测试完成"

echo ""
echo "=== 执行性能测试 C1-C4 ==="

# C1 文件大小性能测试
echo "执行 C1 文件大小性能测试..."
python3 C1/test_C1_file_size_performance.py
echo "C1 测试完成"

# C2 块大小敏感性测试
echo "执行 C2 块大小敏感性测试..."
python3 C2/test_C2_blocksize_sensitivity.py
echo "C2 测试完成"

# C3 并发性能测试
echo "执行 C3 并发性能测试..."
python3 C3/test_C3_concurrency_performance.py
echo "C3 测试完成"

# C4 网络条件测试
echo "执行 C4 网络条件测试..."
python3 C4/test_C4_network_conditions.py
echo "C4 测试完成"

echo ""
echo "=== 收集测试结果 ==="

# 收集所有测试结果
python3 collect_results.py

echo ""
echo "=== 测试完成 ==="
echo "结束时间: $(date)"
echo ""
echo "测试结果已保存到各测试目录的 results.json 文件中"
echo "详细日志请查看各测试目录的 test.log 文件"