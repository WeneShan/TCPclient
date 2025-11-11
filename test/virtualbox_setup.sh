#!/bin/bash
# STEP协议测试环境配置脚本
# 用于在VirtualBox环境中设置和配置测试环境

set -e

# 配置参数
VM_NAME_SERVER="STEP-Server"
VM_NAME_CLIENT1="STEP-Client1"
VM_NAME_CLIENT2="STEP-Client2"
VM_NAME_CLIENT3="STEP-Client3"

VM_MEMORY_SERVER="1024"
VM_MEMORY_CLIENT="512"

NETWORK_NAME="step_internal_network"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查VirtualBox是否安装
check_virtualbox() {
    log_info "检查VirtualBox安装状态..."
    if ! command -v VBoxManage &> /dev/null; then
        log_error "VirtualBox未安装或不在PATH中"
        log_info "请先安装VirtualBox: https://www.virtualbox.org/wiki/Downloads"
        exit 1
    fi
    log_success "VirtualBox已安装"
}

# 创建内部网络
create_network() {
    log_info "创建内部网络: $NETWORK_NAME"
    
    # 检查网络是否已存在
    if VBoxManage list hostonlyifs | grep -q "Name:.*$NETWORK_NAME"; then
        log_warning "网络 $NETWORK_NAME 已存在"
        return 0
    fi
    
    # 创建host-only网络
    VBoxManage hostonlyif create
    
    # 获取新创建的网络接口
    HOSTONLY_IF=$(VBoxManage list hostonlyifs | grep "Name:" | tail -1 | awk '{print $2}')
    
    # 配置网络接口IP
    VBoxManage hostonlyif ipconfig "$HOSTONLY_IF" --ip 192.168.100.1 --netmask 255.255.255.0
    
    log_success "内部网络 $NETWORK_NAME 创建完成，IP: 192.168.100.1"
}

# 创建虚拟机
create_vm() {
    local vm_name=$1
    local vm_memory=$2
    local vm_type="Ubuntu64"
    
    log_info "创建虚拟机: $vm_name"
    
    # 检查VM是否已存在
    if VBoxManage list vms | grep -q "\"$vm_name\""; then
        log_warning "虚拟机 $vm_name 已存在"
        return 0
    fi
    
    # 创建虚拟机
    VBoxManage createvm --name "$vm_name" --ostype "$vm_type" --register
    
    # 配置内存
    VBoxManage modifyvm "$vm_name" --memory $vm_memory
    
    # 配置启动顺序
    VBoxManage modifyvm "$vm_name" --boot1 dvd --boot2 disk --boot3 none --boot4 none
    
    # 启用EFI（可选）
    # VBoxManage modifyvm "$vm_name" --firmware efi
    
    # 配置网络适配器
    VBoxManage modifyvm "$vm_name" --nic1 hostonly --hostonlyadapter1 "$NETWORK_NAME"
    
    # 启用VRDE（远程桌面）
    VBoxManage modifyvm "$vm_name" --vrde on --vrdeport 3389
    
    log_success "虚拟机 $vm_name 创建完成"
}

# 创建并附加存储
create_storage() {
    local vm_name=$1
    local disk_size="20480"  # 20GB
    local iso_path=$2
    
    log_info "为虚拟机 $vm_name 创建存储设备"
    
    # 创建存储控制器
    VBoxManage storagectl "$vm_name" --name "SATA Controller" --add sata --controller IntelAhci
    
    # 创建并附加硬盘
    VBoxManage createhd --filename "${vm_name}_disk.vdi" --size $disk_size
    VBoxManage storageattach "$vm_name" --storagectl "SATA Controller" --port 0 --device 0 --type hdd --medium "${vm_name}_disk.vdi"
    
    # 附加ISO镜像
    if [ -f "$iso_path" ]; then
        VBoxManage storagectl "$vm_name" --name "IDE Controller" --add ide --controller PIIX4
        VBoxManage storageattach "$vm_name" --storagectl "IDE Controller" --port 1 --device 0 --type dvddrive --medium "$iso_path"
        log_success "ISO镜像 $iso_path 已附加到 $vm_name"
    else
        log_warning "ISO镜像 $iso_path 不存在，跳过ISO附加"
    fi
}

# 配置网络带宽限制（在Ubuntu系统内使用tc命令）
setup_network_control() {
    local vm_name=$1
    log_info "为虚拟机 $vm_name 配置网络控制脚本"
    
    # 这里可以生成一个脚本来在虚拟机内部设置tc命令
    cat > "${vm_name}_network_setup.sh" << 'EOF'
#!/bin/bash
# 虚拟机内部网络控制脚本

# 限制带宽到1Mbps
limit_bandwidth() {
    sudo tc qdisc add dev eth0 root handle 1: tbf rate 1mbit burst 32kbit latency 400ms
    echo "带宽限制设置为1Mbps"
}

# 添加延迟
add_delay() {
    local delay_ms=$1
    sudo tc qdisc add dev eth0 root netem delay ${delay_ms}ms
    echo "网络延迟设置为${delay_ms}ms"
}

# 添加丢包
add_loss() {
    local loss_percent=$1
    sudo tc qdisc add dev eth0 root netem loss ${loss_percent}%
    echo "丢包率设置为${loss_percent}%"
}

# 清除网络控制
clear_network() {
    sudo tc qdisc del dev eth0 root
    echo "网络控制已清除"
}

# 显示网络状态
show_status() {
    sudo tc qdisc show dev eth0
}

case "$1" in
    limit)
        limit_bandwidth
        ;;
    delay)
        add_delay ${2:-200}
        ;;
    loss)
        add_loss ${2:-1}
        ;;
    clear)
        clear_network
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法: $0 {limit|delay [ms]|loss [%]|clear|status}"
        exit 1
        ;;
esac
EOF
    
    chmod +x "${vm_name}_network_setup.sh"
    log_success "网络控制脚本已创建: ${vm_name}_network_setup.sh"
}

# 启动虚拟机
start_vm() {
    local vm_name=$1
    local mode=$2  # headless, gui, separate
    
    log_info "启动虚拟机: $vm_name (模式: $mode)"
    
    case $mode in
        "headless")
            VBoxManage startvm "$vm_name" --type headless
            ;;
        "gui")
            VBoxManage startvm "$vm_name" --type gui
            ;;
        "separate")
            VBoxManage startvm "$vm_name" --type separate
            ;;
        *)
            VBoxManage startvm "$vm_name" --type headless
            ;;
    esac
    
    log_success "虚拟机 $vm_name 已启动"
}

# 停止虚拟机
stop_vm() {
    local vm_name=$1
    log_info "停止虚拟机: $vm_name"
    VBoxManage controlvm "$vm_name" poweroff
    log_success "虚拟机 $vm_name 已停止"
}

# 删除虚拟机
delete_vm() {
    local vm_name=$1
    log_warning "删除虚拟机: $vm_name"
    
    # 停止虚拟机
    VBoxManage controlvm "$vm_name" poweroff 2>/dev/null || true
    
    # 等待停止
    sleep 5
    
    # 卸载存储设备
    VBoxManage list vms | grep "$vm_name" && {
        VBoxManage storageattach "$vm_name" --storagectl "IDE Controller" --port 1 --device 0 --medium none 2>/dev/null || true
        VBoxManage storageattach "$vm_name" --storagectl "SATA Controller" --port 0 --device 0 --medium none 2>/dev/null || true
    }
    
    # 删除硬盘文件
    rm -f "${vm_name}_disk.vdi"
    
    # 删除网络控制脚本
    rm -f "${vm_name}_network_setup.sh"
    
    # 删除虚拟机
    VBoxManage unregistervm "$vm_name" --delete
    
    log_success "虚拟机 $vm_name 已删除"
}

# 完整环境设置
setup_complete_environment() {
    log_info "开始设置完整的STEP测试环境..."
    
    # 检查VirtualBox
    check_virtualbox
    
    # 创建网络
    create_network
    
    # 创建服务器虚拟机
    create_vm "$VM_NAME_SERVER" "$VM_MEMORY_SERVER"
    
    # 创建客户端虚拟机
    create_vm "$VM_NAME_CLIENT1" "$VM_MEMORY_CLIENT"
    create_vm "$VM_NAME_CLIENT2" "$VM_MEMORY_CLIENT"
    create_vm "$VM_NAME_CLIENT3" "$VM_MEMORY_CLIENT"
    
    # 这里需要用户提供Ubuntu ISO路径
    local iso_path="$1"
    if [ -n "$iso_path" ] && [ -f "$iso_path" ]; then
        create_storage "$VM_NAME_SERVER" "$iso_path"
        create_storage "$VM_NAME_CLIENT1" "$iso_path"
        create_storage "$VM_NAME_CLIENT2" "$iso_path"
        create_storage "$VM_NAME_CLIENT3" "$iso_path"
    else
        log_warning "请提供Ubuntu ISO路径来完成存储配置"
        log_info "用法: $0 setup_complete /path/to/ubuntu.iso"
    fi
    
    # 创建网络控制脚本
    setup_network_control "$VM_NAME_SERVER"
    setup_network_control "$VM_NAME_CLIENT1"
    
    log_success "完整环境设置完成"
    log_info "接下来的步骤："
    log_info "1. 手动安装Ubuntu系统到每个虚拟机"
    log_info "2. 在服务器上部署server.py"
    log_info "3. 在客户端上部署client.py和测试脚本"
    log_info "4. 使用 start_vms 启动所有虚拟机"
}

# 启动所有虚拟机
start_all_vms() {
    log_info "启动所有虚拟机..."
    start_vm "$VM_NAME_SERVER" "headless"
    start_vm "$VM_NAME_CLIENT1" "headless"
    start_vm "$VM_NAME_CLIENT2" "headless"
    start_vm "$VM_NAME_CLIENT3" "headless"
    log_success "所有虚拟机已启动"
    log_info "可以使用VRDE连接查看虚拟机状态"
}

# 停止所有虚拟机
stop_all_vms() {
    log_info "停止所有虚拟机..."
    stop_vm "$VM_NAME_SERVER"
    stop_vm "$VM_NAME_CLIENT1"
    stop_vm "$VM_NAME_CLIENT2"
    stop_vm "$VM_NAME_CLIENT3"
    log_success "所有虚拟机已停止"
}

# 清理所有资源
cleanup_all() {
    log_warning "清理所有测试资源..."
    stop_all_vms
    delete_vm "$VM_NAME_CLIENT3"
    delete_vm "$VM_NAME_CLIENT2"
    delete_vm "$VM_NAME_CLIENT1"
    delete_vm "$VM_NAME_SERVER"
    log_success "所有资源已清理"
}

# 显示虚拟机状态
show_status() {
    log_info "虚拟机状态："
    VBoxManage list vms
    echo
    log_info "运行中的虚拟机："
    VBoxManage list runningvms
}

# 主函数
main() {
    case "${1:-help}" in
        "check")
            check_virtualbox
            show_status
            ;;
        "network")
            create_network
            ;;
        "setup")
            shift
            setup_complete_environment "$@"
            ;;
        "start")
            start_all_vms
            ;;
        "stop")
            stop_all_vms
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup_all
            ;;
        "help"|*)
            echo "STEP测试环境配置脚本"
            echo
            echo "用法:"
            echo "  $0 check                    - 检查VirtualBox安装状态"
            echo "  $0 network                  - 创建内部网络"
            echo "  $0 setup [iso_path]         - 设置完整环境"
            echo "  $0 start                    - 启动所有虚拟机"
            echo "  $0 stop                     - 停止所有虚拟机"
            echo "  $0 status                   - 显示虚拟机状态"
            echo "  $0 cleanup                  - 清理所有资源"
            echo "  $0 help                     - 显示帮助信息"
            echo
            echo "示例:"
            echo "  $0 setup /path/to/ubuntu-22.04.iso"
            echo "  $0 start"
            ;;
    esac
}

# 运行主函数
main "$@"