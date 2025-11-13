# VirtualBox Ubuntu 虚拟机测试指南

## 概述

本指南详细说明如何在 VirtualBox Ubuntu 虚拟机环境中运行 STEP 协议测试。测试架构已经重构，假设服务器已经在另一个虚拟机中运行，测试在客户端虚拟机中执行。

## 系统架构

### 虚拟机配置
- **服务器虚拟机**: STEP-Server (Ubuntu 22.04)
  - IP: 192.168.100.2
  - 端口: 1379
  - 运行服务器程序: `python3 server/server.py --ip 192.168.100.2 --port 1379`

- **客户端虚拟机**: STEP-Client (Ubuntu 22.04)  
  - IP: 192.168.100.3
  - 运行测试程序

### 网络配置
- 使用 VirtualBox 仅主机网络
- 服务器 IP: 192.168.100.2
- 客户端 IP: 192.168.100.3
- 子网掩码: 255.255.255.0

## 环境准备

### 1. 虚拟机基础配置

在两台虚拟机中执行以下操作：

```bash
# 更新系统
sudo apt update
sudo apt upgrade -y

# 安装必要软件
sudo apt install -y python3 python3-pip git

# 安装项目依赖
pip3 install matplotlib numpy
```

### 2. 项目部署

在客户端虚拟机中部署项目代码：

```bash
# 克隆或复制项目到虚拟机
cd /home/stepuser
# 通过共享文件夹或git克隆获取项目代码

# 设置项目路径
export PROJECT_PATH="/home/stepuser/STEP-Project/"

# 确保测试文件目录存在
mkdir -p $PROJECT_PATH/test/test_data
```

### 3. 网络连通性测试

在客户端虚拟机中测试服务器连接：

```bash
# 检查服务器是否可达
ping 192.168.100.2

# 检查服务器端口是否开放
telnet 192.168.100.2 1379
```

## 测试执行

### 前提条件

1. **服务器运行**: 确保服务器虚拟机正在运行并启动服务器程序
2. **网络连通**: 客户端能 ping 通服务器
3. **项目部署**: 项目代码已部署到客户端虚拟机

### 手动测试执行

在客户端虚拟机中运行单个测试：

```bash
cd /home/stepuser/STEP-Project/

# 运行 A1 基线测试
python3 test/A1/test_A1_baseline.py

# 运行 A2 极小文件测试  
python3 test/A2/test_A2_edge_files.py

# 运行 C1 性能测试
python3 test/C1/test_C1_file_size_performance.py
```

### 批量测试执行

创建测试脚本 `run_all_vm_tests.sh`：

```bash
#!/bin/bash
# 在客户端虚拟机中运行所有测试

echo "=== STEP 协议虚拟机测试开始 ==="

# 功能性测试
echo "执行功能性测试 A1-A6..."
python3 test/A1/test_A1_baseline.py
python3 test/A2/test_A2_edge_files.py
python3 test/A3/test_A3_tail_block.py
python3 test/A4/test_A4_repeat_upload.py
python3 test/A5/test_A5_auth_error.py
python3 test/A6/test_A6_corrupt_block.py

# 性能测试
echo "执行性能测试 C1-C4..."
python3 test/C1/test_C1_file_size_performance.py
python3 test/C2/test_C2_blocksize_sensitivity.py
python3 test/C3/test_C3_concurrency_performance.py
python3 test/C4/test_C4_network_conditions.py

echo "=== 所有测试完成 ==="
```

## 测试配置

### 配置文件

测试配置在 [`vm_test_utils.py`](test/vm_test_utils.py:15) 中的 `VMTestConfig` 类：

```python
class VMTestConfig:
    SERVER_IP = "192.168.100.2"      # 服务器IP
    SERVER_PORT = 1379               # 服务器端口
    STUDENT_ID = "testuser123"       # 测试用户名
    
    # 测试文件大小配置
    TEST_FILE_SIZE_1KB = 1024
    TEST_FILE_SIZE_100KB = 100 * 1024
    TEST_FILE_SIZE_1MB = 1024 * 1024
    TEST_FILE_SIZE_10MB = 10 * 1024 * 1024
    TEST_FILE_SIZE_50MB = 50 * 1024 * 1024
```

### 自定义配置

要修改测试配置，可以：

1. 直接编辑 `vm_test_utils.py` 中的配置类
2. 创建自定义配置文件并导入
3. 通过环境变量覆盖默认配置

## 测试结果

### 结果文件位置

测试结果保存在各测试目录中：

```
/home/stepuser/STEP-Project/test/
├── A1/
│   ├── test.log          # 详细测试日志
│   └── results.json      # 结构化测试结果
├── A2/
├── C1/
│   ├── test.log
│   └── results.json
└── ...
```

### 结果文件格式

`results.json` 格式示例：

```json
{
  "test_name": "A1",
  "test_description": "基线：单客户端标准文件上传",
  "start_time": "2023-12-01T10:00:00",
  "end_time": "2023-12-01T10:05:30", 
  "status": "PASSED",
  "final_result": "MD5校验一致，上传成功",
  "test_cases": [
    {
      "name": "A1_Baseline_Upload",
      "file_size": 10485760,
      "duration": 12.34,
      "local_md5": "abc123...",
      "server_md5": "abc123...",
      "file_integrity": true,
      "upload_success": true
    }
  ]
}
```

## 故障排除

### 常见问题

#### 1. 服务器连接失败

**症状**: 测试报告 "服务器连接失败"

**解决方案**:
```bash
# 检查服务器是否运行
ps aux | grep "python3.*server.py"

# 检查网络连通性
ping 192.168.100.2
telnet 192.168.100.2 1379

# 检查防火墙设置
sudo ufw status
```

#### 2. 文件上传失败

**症状**: 客户端连接成功但上传失败

**解决方案**:
- 检查服务器磁盘空间
- 验证文件权限
- 查看服务器日志

#### 3. MD5 校验失败

**症状**: 文件上传成功但 MD5 校验失败

**解决方案**:
- 检查网络稳定性
- 验证服务器和客户端的文件系统
- 重新运行测试

### 调试模式

启用详细日志记录：

```python
# 在 vm_test_utils.py 中修改
VMTestConfig.LOG_LEVEL = logging.DEBUG
```

## 性能优化建议

### 1. 虚拟机资源配置

- **内存**: 服务器虚拟机建议 4GB，客户端虚拟机建议 2GB
- **CPU**: 为每个虚拟机分配 2 个 CPU 核心
- **磁盘**: 使用 SSD 存储以提高 I/O 性能

### 2. 网络优化

- 使用 VirtIO 网络适配器
- 启用硬件加速
- 调整 MTU 大小

### 3. 测试优化

- 避免在测试期间运行其他高负载程序
- 定期清理临时文件
- 使用适当的测试文件大小

## 扩展测试

### 添加新测试用例

1. 在相应目录下创建测试脚本
2. 导入 `vm_test_utils` 模块
3. 遵循现有的测试结构
4. 保存结果到 `results.json`

### 自定义测试场景

修改测试配置或创建新的测试场景类来测试特定功能。

## 重要提示

1. **环境隔离**: 测试环境应与开发环境隔离
2. **数据备份**: 定期备份重要的测试结果
3. **版本控制**: 保持测试代码与协议版本同步
4. **文档更新**: 测试架构变更时及时更新文档

## 技术支持

如需技术支持，请：
1. 检查测试日志文件
2. 验证网络配置
3. 确认服务器状态
4. 查阅项目文档

---

*最后更新: 2024年1月*
*版本: 2.0 (虚拟机专用版)*