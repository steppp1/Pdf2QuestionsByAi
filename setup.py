#!/usr/bin/env python3
"""
PDF2Question 项目安装脚本
帮助用户快速安装依赖和配置项目
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_step(step, description):
    """打印安装步骤"""
    print(f"\n{'='*60}")
    print(f"步骤 {step}: {description}")
    print('='*60)

def run_command(cmd, description):
    """运行命令并处理错误"""
    print(f"执行: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        print("✅ 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def check_python_version():
    """检查Python版本"""
    print_step(1, "检查Python版本")
    
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 7):
        print("❌ 错误: 需要Python 3.7或更高版本")
        return False
    
    print("✅ Python版本满足要求")
    return True

def install_dependencies():
    """安装Python依赖"""
    print_step(2, "安装Python依赖")
    
    if not os.path.exists("requirements.txt"):
        print("❌ 错误: 找不到requirements.txt文件")
        return False
    
    return run_command("pip install -r requirements.txt", "安装依赖包")

def setup_env_file():
    """设置环境配置文件"""
    print_step(3, "配置环境文件")
    
    env_file = ".env"
    env_example = ".env.example"
    
    if os.path.exists(env_file):
        print(f"✅ {env_file} 文件已存在")
        return True
    
    if os.path.exists(env_example):
        shutil.copy2(env_example, env_file)
        print(f"✅ 已从 {env_example} 创建 {env_file}")
        print("请编辑 .env 文件并设置您的 SILICONFLOW_API_KEY")
        return True
    else:
        # 创建基本的.env文件
        env_content = """# PDF2Question 项目环境配置

# === SiliconFlow API配置 (必需) ===
SILICONFLOW_API_KEY=YOUR_SILICONFLOW_API_KEY_HERE
SILICONFLOW_API_BASE=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL_NAME=Qwen/Qwen3-8B

# === 应用配置 ===
DEFAULT_OUTPUT_DIR=./output
DEFAULT_TEMP_DIR=temp_json
MAX_TOKENS=8192
TEMPERATURE=0.1
TOP_P=0.9
REQUEST_TIMEOUT=120.0

# === PDF处理配置 ===
DEFAULT_PDF_MODE=auto
MAX_TEXT_LENGTH=50000
MAX_QUESTIONS_PER_BATCH=100

# === 日志配置 ===
LOG_LEVEL=INFO

# === 默认题目配置 ===
DEFAULT_SUBJECT=gongji
DEFAULT_MODULE=law
DEFAULT_DIFFICULTY=medium
DEFAULT_TITLE=法律刷题课
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"✅ 已创建 {env_file} 文件")
        print("请编辑 .env 文件并设置您的 SILICONFLOW_API_KEY")
        return True

def check_magic_pdf():
    """检查magic-pdf工具"""
    print_step(4, "检查magic-pdf工具")
    
    try:
        result = subprocess.run("magic-pdf --version", shell=True, 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ magic-pdf 已安装")
            print(f"版本信息: {result.stdout.strip()}")
            return True
        else:
            print("❌ magic-pdf 未安装或版本不兼容")
            print("请参考 magic-pdf 官方文档进行安装")
            return False
    except Exception:
        print("❌ magic-pdf 未安装")
        print("请参考以下链接安装 magic-pdf:")
        print("https://github.com/opendatalab/MinerU")
        return False

def run_test():
    """运行测试"""
    print_step(5, "运行基本测试")
    
    # 测试配置模块
    try:
        from config import config
        print("✅ 配置模块导入成功")
        
        # 打印配置摘要
        config.print_config_summary()
        
        if config.validate_api_key():
            print("✅ API密钥已配置")
        else:
            print("⚠️  警告: API密钥未配置，请在 .env 文件中设置 SILICONFLOW_API_KEY")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置模块测试失败: {e}")
        return False

def main():
    """主函数"""
    print("PDF2Question 项目安装程序")
    print("="*60)
    
    success_count = 0
    total_steps = 5
    
    # 步骤1: 检查Python版本
    if check_python_version():
        success_count += 1
    
    # 步骤2: 安装依赖
    if install_dependencies():
        success_count += 1
    
    # 步骤3: 设置环境文件
    if setup_env_file():
        success_count += 1
    
    # 步骤4: 检查magic-pdf
    if check_magic_pdf():
        success_count += 1
    
    # 步骤5: 运行测试
    if run_test():
        success_count += 1
    
    # 总结
    print("\n" + "="*60)
    print("安装总结")
    print("="*60)
    print(f"完成步骤: {success_count}/{total_steps}")
    
    if success_count == total_steps:
        print("🎉 安装完成! 所有步骤都成功执行")
        print("\n接下来您可以:")
        print("1. 编辑 .env 文件设置您的 SILICONFLOW_API_KEY")
        print("2. 运行示例: python run_example.py")
        print("3. 转换PDF: python main.py -i 示例.pdf -o ./output")
    else:
        print("⚠️  安装过程中有一些问题，请检查上述错误信息")
        if success_count >= 3:
            print("核心功能应该可以正常使用")
    
    print("\n如需帮助，请查看 README.md 或提交Issue")

if __name__ == "__main__":
    main() 