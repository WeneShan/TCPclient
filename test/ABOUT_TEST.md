# STEP 协议测试框架说明

## 概述

本测试框架用于验证 STEP 协议文件传输系统的功能和性能。测试已经重构为适合在 VirtualBox Ubuntu 虚拟机环境中运行。

## 测试架构

### 新的测试架构

测试框架已经重构，移除了对 [`test_utils.py`](test/test_utils.py:1) 中虚拟机管理功能的依赖。新的架构基于：

- **服务器虚拟机**: 预配置的 Ubuntu 虚拟机，运行 STEP 服务器程序
- **客户端虚拟机**: 运行测试程序的 Ubuntu 虚拟机  
- **仅主机网络**: 通过 VirtualBox 仅主机网络连接

### 核心组件

1. **[`vm_test_utils.py`](test/vm_test_utils.py:1)** - 新的测试工具模块
   - `VMTestConfig`: 测试配置管理
   - `VMTestLogger`: 日志记录
   - `VMFileManager`: 测试文件管理
   - `VMNetworkTester`: 网络测试功能

2. **测试脚本**: 所有测试现在直接使用 STEP 协议客户端进行通信

## 测试分类

### A系列 - 功能性测试

- **[`A1/test_A1_baseline.py`](test/A1/test_A1_baseline.py:1)**: 基线测试 - 标准文件上传验证
- **[`A2/test_A2_edge_files.py`](test/A2/test_A2_edge_files.py:1)**: 极小文件测试 - 0字节和1字节文件
- **[`A3/test_A3_tail_block.py`](test/A3/test_A3_tail_block.py:1)**: 尾块测试 - 非整数块大小文件
- **[`A4/test_A4_repeat_upload.py`](test/A4/test_A4_repeat_upload.py:1)**: 重复上传测试 - 同名文件处理
- **[`A5/test_A5_auth_error.py`](test/A5/test_A5_auth_error.py:1)**: 认证错误测试 - 无效凭证处理
- **[`A6/test_A6_corrupt_block.py`](test/A6/test_A6_corrupt_block.py:1)**: 块损坏测试 - 重传机制验证

### C系列 - 性能测试

- **[`C1/test_C1_file_size_performance.py`](test/C1/test_C1_file_size_performance.py:1)**: 文件大小性能测试
- **[`C2/test_C2_blocksize_sensitivity.py`](test/C2/test_C2_blocksize_sensitivity.py:1)**: 块大小敏感性测试
- **[`C3/test_C3_concurrency_performance.py`](test/C3/test_C3_concurrency_performance.py:1)**: 并发性能测试
- **[`C4/test_C4_network_conditions.py`](test/C4/test_C4_network_conditions.py:1)**: 网络条件测试

## 环境要求

### 硬件要求
- Windows 11 主机系统
- VirtualBox 6.1 或更高版本
- 至少 8GB RAM
- 20GB 可用磁盘空间

### 软件要求
- 两台 Ubuntu 22.04 虚拟机
- Python 3.8+
- 项目依赖包 (参见 [`requirements.txt`](../requirements.txt:1))

### 网络配置
- 服务器虚拟机: 192.168.100.2
- 客户端虚拟机: 192.168.100.3
- 仅主机网络适配器

## 测试执行

### 前提条件

1. **服务器配置**: 服务器虚拟机必须运行 STEP 服务器
   ```bash
   python3 server/server.py --ip 192.168.100.2 --port 1379
   ```

2. **网络连通性**: 客户端必须能访问服务器
   ```bash
   ping 192.168.100.2
   telnet 192.168.100.2 1379
   ```

### 执行步骤

在客户端虚拟机中运行测试：

```bash
# 单个测试执行
cd /home/stepuser/STEP-Project/
python3 test/A1/test_A1_baseline.py

# 批量测试执行
chmod +x test/run_all_vm_tests.sh
./test/run_all_vm_tests.sh
```

### 测试结果

每个测试生成：
- `test.log`: 详细执行日志
- `results.json`: 结构化测试结果

## 配置说明

### 测试配置

主要配置在 [`VMTestConfig`](test/vm_test_utils.py:15) 类中：

```python
SERVER_IP = "192.168.100.2"      # 服务器IP地址
SERVER_PORT = 1379               # 服务器端口
STUDENT_ID = "testuser123"       # 测试用户名
LOG_LEVEL = logging.INFO         # 日志级别
```

### 文件配置

测试使用的文件大小定义：

```python
TEST_FILE_SIZE_1KB = 1024
TEST_FILE_SIZE_100KB = 100 * 1024
TEST_FILE_SIZE_1MB = 1024 * 1024
TEST_FILE_SIZE_10MB = 10 * 1024 * 1024
TEST_FILE_SIZE_50MB = 50 * 1024 * 1024
```

## 结果分析

### 结果文件格式

每个测试目录中的 `results.json` 包含：

```json
{
  "test_name": "测试标识",
  "test_description": "测试描述",
  "start_time": "开始时间",
  "end_time": "结束时间",
  "status": "PASSED/FAILED",
  "final_result": "测试结果摘要",
  "test_cases": [
    {
      "name": "测试用例名称",
      "file_size": 文件大小,
      "duration": 执行时间,
      "local_md5": "本地文件MD5",
      "server_md5": "服务器文件MD5", 
      "file_integrity": true/false,
      "upload_success": true/false
    }
  ]
}
```

### 性能指标

性能测试额外包含：

```json
{
  "performance_metrics": {
    "throughput_mbps": 吞吐量,
    "concurrent_clients": 并发客户端数,
    "average_latency": 平均延迟,
    "success_rate": 成功率
  }
}
```

## 故障排除

### 常见问题

1. **服务器连接失败**
   - 检查服务器是否运行
   - 验证网络配置
   - 确认防火墙设置

2. **文件上传失败**  
   - 检查服务器磁盘空间
   - 验证文件权限
   - 查看服务器日志

3. **MD5 校验失败**
   - 检查网络稳定性
   - 验证文件系统完整性
   - 重新运行测试

### 调试模式

启用详细日志：

```python
# 修改 vm_test_utils.py
VMTestConfig.LOG_LEVEL = logging.DEBUG
```

## 文件说明

### 保留的文件

- **测试脚本**: 所有 `test_*.py` 文件
- **工具模块**: [`vm_test_utils.py`](test/vm_test_utils.py:1)
- **测试数据**: `test_data/` 目录
- **配置文档**: [`VirtualBox_Ubuntu_Test_Guide.md`](test/VirtualBox_Ubuntu_Test_Guide.md:1)
- **结果收集**: [`collect_results.py`](test/collect_results.py:1)

### 已移除的文件

- 旧的虚拟机管理工具 [`test_utils.py`](test/test_utils.py:1)
- Windows 批处理脚本 (已由 shell 脚本替代)
- 过时的配置文档

## 扩展开发

### 添加新测试

1. 创建测试脚本文件
2. 导入 [`vm_test_utils`](test/vm_test_utils.py:1) 模块
3. 遵循现有的测试结构
4. 保存结果到 `results.json`

### 自定义配置

通过修改 [`VMTestConfig`](test/vm_test_utils.py:15) 类或创建子类来自定义测试行为。

## 版本历史

- **v2.0**: 重构为虚拟机专用测试框架
- **v1.0**: 原始测试框架（已弃用）

---

*最后更新: 2024年1月*
*版本: 2.0*
