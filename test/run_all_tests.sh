#!/bin/bash
# 运行所有STEP协议测试的自动化脚本

set -e

# 配置
TEST_DIR="test"
PYTHON="python3"

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

# 检查Python版本
check_python() {
    if ! command -v $PYTHON &> /dev/null; then
        log_error "Python3未找到，请先安装Python3"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON --version 2>&1)
    log_info "使用Python版本: $PYTHON_VERSION"
}

# 检查测试文件
check_test_files() {
    log_info "检查测试文件..."
    
    local missing_files=0
    
    # 检查必要的测试脚本
    for test_script in "$TEST_DIR"/A*/*.py "$TEST_DIR"/C*/*.py; do
        if [ ! -f "$test_script" ]; then
            log_warning "测试脚本不存在: $test_script"
            missing_files=$((missing_files + 1))
        fi
    done
    
    # 检查必要工具文件
    if [ ! -f "$TEST_DIR/test_utils.py" ]; then
        log_error "缺少测试工具文件: $TEST_DIR/test_utils.py"
        missing_files=$((missing_files + 1))
    fi
    
    if [ $missing_files -gt 0 ]; then
        log_error "发现 $missing_files 个缺失文件，请检查测试环境"
        exit 1
    fi
    
    log_success "所有测试文件检查完成"
}

# 设置执行权限
set_executable_permissions() {
    log_info "设置执行权限..."
    chmod +x "$TEST_DIR"/*.sh
    chmod +x "$TEST_DIR"/*.py 2>/dev/null || true
    find "$TEST_DIR" -name "*.py" -exec chmod +x {} \;
    log_success "执行权限设置完成"
}

# 运行功能测试
run_functional_tests() {
    log_info "开始功能性测试..."
    
    local test_cases=("A1" "A2" "A3" "A4" "A5" "A6")
    local passed=0
    local failed=0
    
    for test_case in "${test_cases[@]}"; do
        log_info "运行测试 $test_case..."
        
        if $PYTHON "$TEST_DIR/$test_case/${test_case,,}_"*.py; then
            log_success "$test_case 测试通过"
            passed=$((passed + 1))
        else
            log_error "$test_case 测试失败"
            failed=$((failed + 1))
        fi
        
        # 间隔一下避免资源冲突
        sleep 2
    done
    
    log_info "功能性测试完成: $passed 通过, $failed 失败"
    return $failed
}

# 运行性能测试
run_performance_tests() {
    log_info "开始性能测试..."
    
    local test_cases=("C1" "C2" "C3" "C4")
    local passed=0
    local failed=0
    
    for test_case in "${test_cases[@]}"; do
        log_info "运行性能测试 $test_case..."
        
        if $PYTHON "$TEST_DIR/$test_case/${test_case,,}_"*.py; then
            log_success "$test_case 测试通过"
            passed=$((passed + 1))
        else
            log_warning "$test_case 测试失败或跳过"
            failed=$((failed + 1))
        fi
        
        # 性能测试间隔更长
        sleep 3
    done
    
    log_info "性能测试完成: $passed 通过, $failed 失败"
    return $failed
}

# 收集测试结果
collect_test_results() {
    log_info "收集测试结果..."
    
    if [ -f "$TEST_DIR/collect_results.py" ]; then
        $PYTHON "$TEST_DIR/collect_results.py" --plots
        log_success "测试结果收集完成"
    else
        log_warning "测试结果收集脚本不存在"
    fi
}

# 生成测试报告
generate_test_report() {
    log_info "生成测试报告..."
    
    local report_file="$TEST_DIR/test_summary_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "STEP协议测试报告"
        echo "生成时间: $(date)"
        echo "=" * 50
        echo
        
        # 检查各个测试结果
        for test_dir in "$TEST_DIR"/A* "$TEST_DIR"/C*; do
            if [ -d "$test_dir" ]; then
                test_name=$(basename "$test_dir")
                results_file="$test_dir/results.json"
                
                if [ -f "$results_file" ]; then
                    echo "测试 $test_name:"
                    if grep -q '"status": "PASSED"' "$results_file"; then
                        echo "  状态: 通过"
                    elif grep -q '"status": "FAILED"' "$results_file"; then
                        echo "  状态: 失败"
                    else
                        echo "  状态: 未知"
                    fi
                else
                    echo "测试 $test_name: 结果文件不存在"
                fi
                echo
            fi
        done
        
        echo "测试报告生成完成: $report_file"
    } > "$report_file"
    
    log_success "测试报告已保存: $report_file"
}

# 主函数
main() {
    echo "=================================="
    echo "STEP协议综合测试系统"
    echo "=================================="
    echo
    
    # 初始检查
    check_python
    check_test_files
    set_executable_permissions
    
    echo
    log_info "选择测试类型："
    echo "1. 功能性测试 (A1-A6)"
    echo "2. 性能测试 (C1-C4)"
    echo "3. 全部测试"
    echo "4. 收集结果 (不运行测试)"
    read -p "请选择 [1-4]: " choice
    
    case $choice in
        1)
            run_functional_tests
            collect_test_results
            generate_test_report
            ;;
        2)
            log_warning "性能测试可能需要较长时间，请确保有足够时间"
            read -p "是否继续？ [y/N]: " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                run_performance_tests
                collect_test_results
                generate_test_report
            else
                log_info "性能测试已取消"
            fi
            ;;
        3)
            log_warning "完整测试可能需要较长时间，请确保有足够时间"
            read -p "是否继续？ [y/N]: " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                log_info "开始完整测试流程..."
                functional_failed=0
                performance_failed=0
                
                run_functional_tests || functional_failed=$?
                sleep 5
                
                if [[ $functional_failed -eq 0 ]]; then
                    run_performance_tests || performance_failed=$?
                else
                    log_warning "功能性测试失败，跳过性能测试"
                fi
                
                collect_test_results
                generate_test_report
                
                if [[ $functional_failed -eq 0 && $performance_failed -eq 0 ]]; then
                    log_success "所有测试完成"
                else
                    log_warning "部分测试失败，请检查结果"
                fi
            else
                log_info "完整测试已取消"
            fi
            ;;
        4)
            collect_test_results
            generate_test_report
            ;;
        *)
            log_error "无效选择"
            exit 1
            ;;
    esac
    
    echo
    log_info "测试执行完成！"
    log_info "查看详细结果请参考 test/ 目录下的各个结果文件"
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi