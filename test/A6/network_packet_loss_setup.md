# A6 测试 - 网络丢包环境设置指南

## 方法一：使用 tc (Traffic Control) 命令

### 前提条件
- Ubuntu 虚拟机
- root 权限
- 安装 iproute2 包（通常已预装）

### 设置步骤

1. **识别网络接口**
   ```bash
   # 查看网络接口名称
   ip addr show
   # 通常为 ens33, ens38, enp0s3 等
   ```

2. **设置丢包率（10%）**
   ```bash
   # 设置10%丢包率
   sudo tc qdisc add dev ens33 root netem loss 10%
   
   # 验证设置
   tc qdisc show dev ens33
   ```

3. **运行 A6 测试**
   ```bash
   cd /home/stepuser/STEP-Project/
   python3 test/A6/test_A6_corrupt_block.py
   ```

4. **清除设置**
   ```bash
   sudo tc qdisc del dev ens33 root netem
   ```

### 不同丢包率设置
```bash
# 轻度丢包 (5%)
sudo tc qdisc add dev ens33 root netem loss 5%

# 中度丢包 (15%)
sudo tc qdisc add dev ens33 root netem loss 15%

# 重度丢包 (30%)
sudo tc qdisc add dev ens33 root netem loss 30%
```

## 方法二：VirtualBox 网络适配器设置

### 通过 VirtualBox GUI 设置

1. 关闭虚拟机
2. 打开虚拟机设置
3. 选择"网络" → "适配器1" → "高级"
4. 点击"端口转发"
5. 添加规则，但这种方法主要影响端口转发，不是直接丢包

### 通过 VBoxManage 命令行

```bash
# 在主机上执行（Windows PowerShell）
# 设置网络带宽限制和丢包
VBoxManage bandwidthctl "Ubuntu-Client" add Limit --type network --limit 10m
VBoxManage bandwidthctl "Ubuntu-Client" set Limit --limit 10m
```

## 方法三：使用 iptables 模拟丢包

```bash
# 随机丢弃10%的TCP包（需要root权限）
sudo iptables -A INPUT -p tcp -m statistic --mode random --probability 0.1 -j DROP
sudo iptables -A OUTPUT -p tcp -m statistic --mode random --probability 0.1 -j DROP

# 查看规则
sudo iptables -L

# 清除规则
sudo iptables -F
```

## 方法四：创建自动化脚本

### 自动化设置脚本

创建 `test/A6/setup_packet_loss.sh`：

```bash
#!/bin/bash
# A6 网络丢包环境设置脚本

set -e

INTERFACE="ens33"  # 根据实际情况修改
PACKET_LOSS="10%"  # 丢包率

echo "=== 设置网络丢包环境 ==="

# 检查权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 清除现有规则
echo "清除现有网络规则..."
tc qdisc del dev $INTERFACE root 2>/dev/null || true

# 设置丢包
echo "设置 $PACKET_LOSS 丢包率在接口 $INTERFACE 上..."
tc qdisc add dev $INTERFACE root netem loss $PACKET_LOSS

# 验证设置
echo "当前网络设置:"
tc qdisc show dev $INTERFACE

echo ""
echo "✅ 网络丢包环境设置完成"
echo "现在可以运行 A6 测试: python3 test/A6/test_A6_corrupt_block.py"
echo ""
echo "测试完成后，运行 cleanup_packet_loss.sh 清除设置"
```

### 清理脚本

创建 `test/A6/cleanup_packet_loss.sh`：

```bash
#!/bin/bash
# A6 网络丢包环境清理脚本

set -e

INTERFACE="ens33"  # 根据实际情况修改

echo "=== 清理网络丢包设置 ==="

# 检查权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 清除规则
echo "清除网络规则..."
tc qdisc del dev $INTERFACE root 2>/dev/null || true

# 验证清理
echo "当前网络设置:"
tc qdisc show dev $INTERFACE

echo ""
echo "✅ 网络设置已恢复"
```

## 方法五：修改 A6 测试脚本集成网络设置

### 增强的 A6 测试脚本

我们可以修改 [`test_A6_corrupt_block.py`](test/A6/test_A6_corrupt_block.py:1) 来集成网络设置：

```python
def setup_network_packet_loss(interface="ens33", loss_rate="10%"):
    """设置网络丢包环境"""
    try:
        import subprocess
        # 清除现有规则
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", interface, "root"], 
                      capture_output=True, text=True)
        # 设置新规则
        result = subprocess.run(
            ["sudo", "tc", "qdisc", "add", "dev", interface, "root", "netem", "loss", loss_rate],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"网络设置失败: {e}")
        return False

def cleanup_network_packet_loss(interface="ens33"):
    """清理网络设置"""
    try:
        import subprocess
        result = subprocess.run(
            ["sudo", "tc", "qdisc", "del", "dev", interface, "root"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"网络清理失败: {e}")
        return False
```

## 推荐的测试流程

### 手动测试流程

1. **准备阶段**
   ```bash
   # 在客户端虚拟机中
   cd /home/stepuser/STEP-Project/
   sudo test/A6/setup_packet_loss.sh
   ```

2. **执行测试**
   ```bash
   python3 test/A6/test_A6_corrupt_block.py
   ```

3. **清理阶段**
   ```bash
   sudo test/A6/cleanup_packet_loss.sh
   ```

### 自动化测试流程

创建 `test/A6/run_test_with_packet_loss.sh`：

```bash
#!/bin/bash
# A6 带网络丢包的自动化测试

set -e

echo "=== A6 带网络丢包测试开始 ==="

# 设置网络丢包
echo "设置网络丢包环境..."
sudo test/A6/setup_packet_loss.sh

# 运行测试
echo "执行 A6 测试..."
python3 test/A6/test_A6_corrupt_block.py

# 清理网络设置
echo "清理网络环境..."
sudo test/A6/cleanup_packet_loss.sh

echo "=== A6 测试完成 ==="
```

## 注意事项

1. **权限要求**: tc 命令需要 root 权限
2. **接口名称**: 确保使用正确的网络接口名称
3. **测试影响**: 网络设置会影响所有网络通信，测试期间避免其他网络操作
4. **恢复设置**: 测试后务必清理网络设置
5. **VirtualBox 版本**: 不同版本的 VirtualBox 可能有不同的网络行为

## 故障排除

### 常见问题

1. **tc 命令未找到**
   ```bash
   sudo apt update && sudo apt install iproute2
   ```

2. **接口名称错误**
   ```bash
   ip addr show  # 查看正确的接口名称
   ```

3. **权限不足**
   ```bash
   # 使用 sudo 或切换到 root 用户
   sudo -i
   ```

4. **规则已存在**
   ```bash
   # 先清除现有规则
   sudo tc qdisc del dev ens33 root
   ```

## 验证设置

设置完成后，可以使用以下命令验证：

```bash
# 查看当前网络规则
tc qdisc show dev ens33

# 测试网络连通性（观察丢包）
ping 192.168.100.2

# 使用更详细的网络测试
sudo tcpdump -i ens33 -n
```

通过以上方法，您可以有效地在 VirtualBox Ubuntu 环境中设置网络丢包，从而测试 STEP 协议的块损坏重传机制。