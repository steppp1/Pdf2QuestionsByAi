#!/usr/bin/env python3
"""
快速示例脚本 - 演示如何使用PDF转题目转换器
"""

import os
import asyncio
from main import PDF2QuestionConverter
from config import config

async def run_example():
    """运行示例转换"""
    print("=" * 50)
    print("   PDF转题目转换器 - 示例运行")
    print("=" * 50)
    
    # 打印配置摘要
    config.print_config_summary()
    print()
    
    # 检查API密钥
    if not config.validate_api_key():
        print("❌ 请先设置环境变量 SILICONFLOW_API_KEY")
        print("   export SILICONFLOW_API_KEY='your-api-key-here'")
        print("   或者在项目根目录创建 .env 文件并添加:")
        print("   SILICONFLOW_API_KEY=your-api-key-here")
        return
    
    # 检查示例文件
    example_pdf = "示例.pdf"
    if not os.path.exists(example_pdf):
        print(f"❌ 找不到示例PDF文件: {example_pdf}")
        print("   请确保项目根目录存在示例PDF文件")
        return
    
    try:
        # 初始化转换器
        converter = PDF2QuestionConverter()
        
        # 设置输出目录
        output_dir = config.DEFAULT_OUTPUT_DIR
        
        print(f"📄 输入文件: {example_pdf}")
        print(f"📁 输出目录: {output_dir}")
        
        # 执行转换
        result_file = await converter.convert_single_pdf(
            example_pdf,
            output_dir,
            mode=config.DEFAULT_PDF_MODE
        )
        
        print(f"\n✅ 转换成功!")
        print(f"📋 题目文件: {result_file}")
        
        # 显示结果统计
        import json
        with open(result_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        print(f"\n📊 转换统计:")
        print(f"   总题目数: {len(questions)}")
        
        # 统计题目类型
        type_counts = {}
        for q in questions:
            q_type = q.get('type', 'unknown')
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
        
        for q_type, count in type_counts.items():
            print(f"   {q_type}: {count} 道")
        
        # 显示前几道题目的预览
        if questions:
            print(f"\n📝 题目预览:")
            for i, q in enumerate(questions[:2]):
                print(f"   题目 {i+1}: {q.get('content', 'N/A')[:80]}...")
                print(f"   类型: {q.get('type', 'N/A')} | 答案: {q.get('correctAnswer', [])}")
        
        print(f"\n🎉 示例运行完成!")
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_example()) 