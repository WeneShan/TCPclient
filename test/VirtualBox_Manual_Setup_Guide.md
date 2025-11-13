# VirtualBox 手动配置指南

## 概述

本指南详细说明如何手动配置 VirtualBox 虚拟机以运行 STEP 协议测试。由于自动虚拟机创建存在技术复杂性，建议采用手动配置方式。

## 系统要求

- VirtualBox 6.0 或更高版本
- Ubuntu 22.04.5 桌面版 ISO 镜像
- 至少 8GB RAM（推荐 16GB）
- 至少 50GB 可用磁盘空间
- 稳定的网络连接

## 虚拟机配置步骤

### 1. 创建服务器虚拟机

#### 1.1 新建虚拟机
1. 打开 VirtualBox
2. 点击"新建"按钮
3. 设置虚拟机名称：`STEP-Server`
4. 类型：Linux
5. 版本：Ubuntu (64-bit)
6. 内存大小：4096 MB
7. 硬盘：现在创建虚拟硬盘
8. 硬盘文件类型：VDI (VirtualBox Disk Image)
9. 存储在物理硬盘上：动态分配
10. 文件位置和大小：至少 25GB

#### 1.2 网络配置
1. 选择虚拟机 → 设置 → 网络
2. 适配器1：NAT
3. 适配器2：仅主机(Host-Only)网络
   - 名称：VirtualBox Host-Only Ethernet Adapter
   - 高级 → 控制芯片：Intel PRO/1000 MT 桌面

#### 1.3 系统配置
1. 设置 → 系统 → 处理器：2个CPU
2. 设置 → 显示 → 显存：128MB
3. 设置 → 存储 → 控制器：IDE → 选择 Ubuntu ISO 镜像

### 2. 创建客户端虚拟机

#### 2.1 新建虚拟机
1. 重复服务器虚拟机的创建步骤
2. 设置虚拟机名称：`STEP-Client`
3. 内存大小：2048 MB
4. 硬盘大小：至少 20GB

#### 2.2 网络配置
1. 适配器1：NAT
2. 适配器2：仅主机(Host-Only)网络（与服务器相同）

### 3. 安装 Ubuntu 系统

#### 3.1 服务器虚拟机安装
1. 启动 STEP-Server 虚拟机
2. 选择"Install Ubuntu"
3. 语言：English
4. 键盘布局：English (US)
5. 更新和其他软件：正常安装
6. 安装类型：清除整个磁盘并安装 Ubuntu
7. 时区：根据实际位置设置
8. 用户信息：
   - 您的姓名：`stepuser`
   - 计算机名：`step-server`
   - 用户名：`stepuser`
   - 密码：`steppass`
9. 等待安装完成并重启

#### 3.2 客户端虚拟机安装
1. 重复服务器安装步骤
2. 计算机名：`step-client`
3. 使用相同的用户名和密码：`stepuser` / `steppass`

### 4. 网络配置

#### 4.1 服务器网络设置
1. 登录服务器虚拟机
2. 打开终端，执行：
```bash
sudo nano /etc/netplan/01-netcfg.yaml
```

3. 添加以下配置：
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      dhcp4: false
      addresses: [192.168.100.2/24]
```

4. 应用配置：
```bash
sudo netplan apply
```

#### 4.2 客户端网络设置
1. 登录客户端虚拟机
2. 打开终端，执行：
```bash
sudo nano /etc/netplan/01-netcfg.yaml
```

3. 添加以下配置：
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      dhcp4: false
      addresses: [192.168.100.3/24]
```

4. 应用配置：
```bash
sudo netplan apply
```

### 5. 项目部署

#### 5.1 在两台虚拟机上安装必要软件
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-pip git

# 安装项目依赖
pip3 install matplotlib numpy
```

#### 5.2 克隆项目代码
```bash
cd /home/stepuser
git clone <项目仓库URL>
# 或者通过共享文件夹复制项目文件
```

#### 5.3 配置共享文件夹（可选）
1. VirtualBox 设置 → 共享文件夹
2. 添加共享文件夹：
   - 文件夹路径：主机项目目录
   - 文件夹名称：STEP-Project
   - 自动挂载：是
   - 只读分配：否

3. 在虚拟机中挂载：
```bash
sudo usermod -a -G vboxsf stepuser
# 重启虚拟机
```

### 6. 验证配置

#### 6.1 网络连通性测试
在客户端虚拟机中执行：
```bash
ping 192.168.100.2
```

#### 6.2 文件传输测试
1. 在服务器启动服务：
```bash
cd /home/stepuser/STEP-Project
python3 server/server.py --ip 192.168.100.2 --port 1379
```

2. 在客户端测试连接：
```bash
cd /home/stepuser/STEP-Project
python3 client.py
```

## 故障排除

### 常见问题

1. **网络无法连接**
   - 检查 VirtualBox 主机仅网络适配器配置
   - 确认防火墙设置
   - 验证 IP 地址配置

2. **共享文件夹无法访问**
   - 确认安装了 VirtualBox Guest Additions
   - 检查用户权限
   - 重启虚拟机

3. **服务启动失败**
   - 检查 Python 版本（需要 Python 3.7+）
   - 验证依赖包安装
   - 查看端口占用情况

### 重要提示

- 确保两台虚拟机使用相同的仅主机网络适配器
- 定期创建虚拟机快照以便恢复
- 测试前确认网络连通性
- 保持 VirtualBox 版本更新

## 后续步骤

完成上述配置后，您可以运行测试脚本：

1. 在主机上运行 `run_all_tests.bat`
2. 选择相应的测试类型
3. 查看测试结果和报告

如需详细测试说明，请参考 `ABOUT_TEST.md` 文件。