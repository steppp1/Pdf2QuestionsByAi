#!/usr/bin/env python3
"""
测试网络错误修复功能
"""

import asyncio
import os
import json
from aiJson2Questions import transform_raw_text_to_mongo_questions

async def test_network_resilience():
    """测试网络容错能力"""
    print("=== 测试网络容错能力 ===\n")
    
    # 检查API密钥
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key or api_key == "YOUR_SILICONFLOW_API_KEY_HERE":
        print("❌ 请设置环境变量 SILICONFLOW_API_KEY")
        return
    
    # 创建一个小的测试数据
    test_data = [
        {"text": "1. 以下哪个是中华人民共和国的根本制度？\nA. 人民代表大会制度\nB. 中国共产党领导的多党合作制度\nC. 人民民主专政\nD. 社会主义制度", "type": "text"},
        {"text": "2. 【判断】中华人民共和国的一切权力属于人民。", "type": "text"}
    ]
    
    print(f"📄 测试数据准备完成，共 {len(test_data)} 条记录")
    
    try:
        print("🔄 开始API调用测试...")
        
        # 测试AI转换功能
        questions = await transform_raw_text_to_mongo_questions(test_data)
        
        if questions:
            print(f"✅ 测试成功！转换得到 {len(questions)} 道题目")
            
            # 显示结果
            for i, q in enumerate(questions, 1):
                print(f"\n题目 {i}:")
                print(f"  内容: {q.get('content', 'N/A')[:100]}...")
                print(f"  类型: {q.get('type', 'N/A')}")
                print(f"  选项数: {len(q.get('options', []))}")
                print(f"  正确答案: {q.get('correctAnswer', [])}")
        else:
            print("⚠️  API调用成功但没有返回题目")
            
    except Exception as e:
        print(f"❌ 测试失败: {type(e).__name__}")
        print(f"错误详情: {str(e)}")
        
        # 提供错误排查建议
        if "ReadError" in str(type(e)):
            print("\n🔧 错误排查建议:")
            print("1. 检查网络连接是否稳定")
            print("2. 可能是服务器暂时不可用，稍后重试")
            print("3. 检查防火墙设置")
        elif "TimeoutException" in str(type(e)):
            print("\n🔧 错误排查建议:")
            print("1. 网络延迟较高，考虑增加超时时间")
            print("2. 检查网络带宽")
        elif "401" in str(e):
            print("\n🔧 错误排查建议:")
            print("1. 检查API密钥是否正确")
            print("2. 检查API密钥是否有效")

if __name__ == "__main__":
    print("开始网络容错测试...")
    asyncio.run(test_network_resilience())
    print("\n测试完成！") 