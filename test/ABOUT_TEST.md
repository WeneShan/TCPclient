# STEP协议测试系统

## 测试内容

### A部分 - 功能性与正确性测试

| 测试项 | 测试内容 | 目的 |
|--------|----------|------|
| A1 | 基线：单客户端标准文件上传 | 验证协议基础流程和MD5校验 |
| A2 | 0字节/1字节文件上传 | 测试极小文件的处理机制 |
| A3 | 文件大小非block_size倍数 | 验证尾块处理正确性 |
| A4 | 重复上传/覆盖策略 | 测试服务器对重复上传的处理 |
| A5 | 错误凭据（Token/Key错误） | 验证错误认证的错误处理 |
| A6 | 错误块内容（传输破坏） | 测试网络异常情况下的恢复能力 |
### B部分 - 鲁棒性
暂缓
### C部分 - 应用层性能测试

| 测试项 | 测试内容 | 目的 |
|--------|----------|------|
| C1 | 不同文件大小上传耗时 | 评估协议扩展性 |
| C2 | 不同block_size影响 | 分析参数敏感性 |
| C3 | 并发客户端性能 | 评估多客户端并发处理能力 |
| C4 | 恶劣网络条件成功率 | 测试网络鲁棒性 |

## 系统要求

### 硬件要求

- **CPU**: 支持虚拟化技术的处理器
- **内存**: 至少4GB RAM（推荐8GB或更多）
- **存储**: 至少20GB可用磁盘空间
- **网络**: 支持Host-only网络配置

### 软件要求

- **主机操作系统**: Linux/Windows/macOS
- **VirtualBox**: 6.0或更高版本
- **Ubuntu ISO**: 22.04 LTS或更高版本（用于虚拟机）
- **Python**: 3.7或更高版本

## 安装与配置

### 1. VirtualBox环境设置

#### 自动化设置（推荐）

```bash
# 进入测试目录
cd test/

# 设置执行权限
chmod +x virtualbox_setup.sh

# 检查VirtualBox安装状态
./virtualbox_setup.sh check

# 创建内部网络
./virtualbox_setup.sh network

# 设置完整测试环境（需要提供Ubuntu ISO路径）
./virtualbox_setup.sh setup /path/to/ubuntu-22.04.iso

# 启动所有虚拟机
./virtualbox_setup.sh start
```

#### 手动设置（备选）

如果自动化脚本无法满足需求，可以手动创建虚拟机：

1. 创建4个虚拟机：
   - 1个服务器虚拟机（1024MB内存）
   - 3个客户端虚拟机（512MB内存）
2. 配置Host-only网络：192.168.100.0/24
3. 安装Ubuntu系统到每个虚拟机

### 2. 测试代码部署

#### 在服务器虚拟机上部署

```bash
# 复制服务器代码
scp server/server.py user@192.168.100.2:~/
scp -r test/ user@192.168.100.2:~/

# 登录服务器虚拟机
ssh user@192.168.100.2

# 安装依赖和启动服务器
sudo apt update
sudo apt install python3 python3-pip
cd ~
python3 server/server.py
```

#### 在客户端虚拟机上部署

```bash
# 复制客户端代码和测试脚本
scp client.py user@192.168.100.3:~/
scp -r test/ user@192.168.100.3:~/
scp -r test_data/ user@192.168.100.3:~/  # 如果需要

# 登录客户端虚拟机
ssh user@192.168.100.3

# 安装依赖
sudo apt update
sudo apt install python3 python3-pip
cd ~

# 运行基础功能测试
python3 test/A1/test_A1_baseline.py

# 运行所有功能测试
for test_dir in A*; do
    python3 "test/${test_dir}/"*.py
done
```

## 测试执行指南

### 基础功能测试执行

#### A1 - 基线测试（必做）

```bash
cd test/A1/
python3 test_A1_baseline.py
```

**预期结果**: 
- 文件上传成功
- MD5校验一致
- 测试日志显示完整的协议流程

#### A2 - 极小文件测试

```bash
cd test/A2/
python3 test_A2_edge_files.py
```

**测试重点**: 0字节和1字节文件的处理机制

#### A3 - 尾块处理测试

```bash
cd test/A3/
python3 test_A3_tail_block.py
```

**测试重点**: 非对齐文件大小的尾块处理

#### A4 - 重复上传测试

```bash
cd test/A4/
python3 test_A4_repeat_upload.py
```

**测试重点**: 服务器对重复上传的处理策略（覆盖/拒绝）

#### A5 - 错误凭据测试

```bash
cd test/A5/
python3 test_A5_auth_error.py
```

**测试重点**: 认证错误的检测和错误处理

#### A6 - 传输错误测试

```bash
cd test/A6/
python3 test_A6_corrupt_block.py
```

**测试重点**: 网络中断和传输错误的恢复能力

### 性能测试执行

#### C1 - 文件大小扩展性测试

```bash
cd test/C1/
python3 test_C1_file_size_performance.py
```

**测试内容**: 1KB, 100KB, 1MB, 10MB, 50MB文件的性能
**测试时长**: 约30-60分钟（取决于网络条件）

#### C2 - block_size敏感性测试

```bash
cd test/C2/
python3 test_C2_blocksize_sensitivity.py
```

**测试内容**: 不同文件大小对应的block_size效果
**测试时长**: 约20-40分钟

#### C3 - 并发性能测试

```bash
cd test/C3/
python3 test_C3_concurrency_performance.py
```

**测试内容**: 1、2、4个客户端并发上传
**测试时长**: 约15-30分钟

#### C4 - 网络鲁棒性测试

```bash
cd test/C4/
sudo python3 test_C4_network_conditions.py
```

**注意**: 需要sudo权限来使用tc命令模拟网络条件
**测试内容**: 带宽限制、延迟、丢包情况下的性能

## 网络条件模拟

### 使用tc命令（Linux虚拟机内）

```bash
# 限制带宽到1Mbps
sudo tc qdisc add dev eth0 root handle 1: tbf rate 1mbit burst 32kbit latency 400ms

# 添加200ms延迟
sudo tc qdisc add dev eth0 root netem delay 200ms

# 添加1%丢包
sudo tc qdisc add dev eth0 root netem loss 1%

# 清除网络条件
sudo tc qdisc del dev eth0 root

# 查看当前网络配置
sudo tc qdisc show dev eth0
```

### 使用脚本自动化

```bash
# 使用创建的网络控制脚本
./STEP-Server_network_setup.sh limit    # 限制带宽
./STEP-Server_network_setup.sh delay 200 # 添加200ms延迟
./STEP-Server_network_setup.sh loss 1    # 添加1%丢包
./STEP-Server_network_setup.sh clear     # 清除条件
./STEP-Server_network_setup.sh status    # 查看状态
```

## 测试结果分析

### 结果文件位置

测试完成后，结果文件保存在各测试目录中：

```
test/
├── A1/
│   ├── test.log          # 详细测试日志
│   └── results.json      # 结构化测试结果
├── A2/
├── A3/
├── C1/
│   ├── test.log
│   ├── results.json
│   └── performance_summary.json  # 性能摘要
└── ...
```

### 结果文件格式

#### results.json 格式

```json
{
  "test_name": "A1",
  "test_description": "基线：单客户端标准文件上传",
  "start_time": "2023-12-01T10:00:00",
  "end_time": "2023-12-01T10:05:30",
  "status": "PASSED|FAILED",
  "final_result": "测试结果描述",
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

### 性能指标分析

#### 吞吐量计算

```bash
# goodput (MB/s) = 文件大小 / 传输时间
goodput = file_size / (duration * 1024 * 1024)
```

#### 成功率统计

```bash
success_rate = successful_uploads / total_uploads
```

#### 公平性评估

```bash
fairness_ratio = min_goodput / max_goodput
```

## 故障排除

### 常见问题

#### 1. 虚拟机无法启动

**原因**: VirtualBox未正确安装或配置
**解决方案**:
```bash
# 检查VirtualBox安装
VBoxManage --version

# 检查虚拟化支持
egrep -c '(vmx|svm)' /proc/cpuinfo
```

#### 2. 网络连接失败

**原因**: Host-only网络未正确配置
**解决方案**:
```bash
# 重置网络配置
./virtualbox_setup.sh cleanup
./virtualbox_setup.sh network
```

#### 3. 测试脚本权限错误

**解决方案**:
```bash
chmod +x *.py
chmod +x *.sh
```

#### 4. Python模块缺失

**解决方案**:
```bash
pip3 install pathlib statistics concurrent.futures
```

### 调试模式

启用详细日志记录：

```python
# 在test_utils.py中设置
TestConfig.LOG_LEVEL = logging.DEBUG
```

### 性能问题诊断

#### 检查CPU和内存使用

```bash
# 在服务器端
top -p $(pgrep python3)

# 在客户端
ps aux | grep client.py
```

#### 检查网络流量

```bash
# 使用tcpdump抓包
sudo tcpdump -i eth0 host 192.168.100.2
```

## 测试报告生成

### 自动化报告生成

```bash
# 使用统一的结果收集脚本
python3 test/collect_results.py

# 生成HTML报告
python3 test/generate_report.py --format html
```

### 手动分析

1. **功能测试结果**:
   - 查看各A1-A6目录下的results.json
   - 检查PASSED/FAILED状态
   - 分析失败原因

2. **性能测试结果**:
   - 分析C1-C4目录下的performance_summary.json
   - 绘制性能趋势图
   - 识别性能瓶颈

3. **综合评估**:
   - 对比不同测试场景的结果
   - 评估协议在各种条件下的表现
   - 提出改进建议

## 最佳实践

### 测试执行顺序

1. **优先执行**: A1基础功能测试
2. **功能验证**: A2-A6功能测试
3. **性能基准**: C1文件大小测试
4. **参数优化**: C2 block_size测试
5. **扩展性测试**: C3并发测试
6. **鲁棒性测试**: C4网络条件测试

### 数据收集建议

- **多次测试**: 每个配置至少运行3次
- **基准记录**: 在理想条件下记录性能基准
- **对比分析**: 对比不同配置下的性能差异
- **错误日志**: 保留详细的错误日志用于分析

### 测试环境维护

- **定期清理**: 清理临时文件和日志
- **配置备份**: 保存成功的测试配置
- **版本控制**: 对测试脚本进行版本管理

## 扩展与定制

### 添加新测试用例

1. 在相应目录下创建测试脚本
2. 继承TestConfig和TestLogger基类
3. 遵循现有的结果保存格式
4. 更新本README文档

### 自定义网络条件

修改`test_C4_network_conditions.py`中的`test_conditions`配置：

```python
test_conditions = [
    {'type': 'custom_condition', 'name': '自定义条件', 'parameters': {...}}
]
```

### 性能监控扩展

可以添加系统资源监控：

```python
import psutil

def monitor_system_resources():
    return {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_io': psutil.disk_io_counters()
    }
```

