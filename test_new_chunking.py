#!/usr/bin/env python3
"""
测试新的切分和拼合功能
"""

import asyncio
import os
import json
from main import PDF2QuestionConverter

async def test_chunking_functionality():
    """测试切分功能"""
    print("=== 测试新的切分和拼合功能 ===\n")
    
    # 检查API密钥
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key or api_key == "YOUR_SILICONFLOW_API_KEY_HERE":
        print("❌ 请设置环境变量 SILICONFLOW_API_KEY")
        return
    
    try:
        # 初始化转换器
        converter = PDF2QuestionConverter(api_key)
        
        # 测试用例1：处理单个JSON文件
        test_json_file = "test.json"  # 假设这是一个大的JSON文件
        if os.path.exists(test_json_file):
            print(f"📄 测试处理JSON文件: {test_json_file}")
            
            output_dir = "test_chunking_output"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = await converter.convert_single_file(
                test_json_file, 
                output_dir
            )
            
            print(f"✅ 测试完成，输出文件: {output_file}")
            
            # 检查生成的目录结构
            print(f"\n📁 检查生成的目录结构:")
            chunks_dir = os.path.join(output_dir, "切片")
            results_dir = os.path.join(output_dir, "results")
            
            if os.path.exists(chunks_dir):
                print(f"  切片目录: {chunks_dir}")
                for item in os.listdir(chunks_dir):
                    item_path = os.path.join(chunks_dir, item)
                    if os.path.isdir(item_path):
                        chunk_count = len([f for f in os.listdir(item_path) if f.endswith('.json')])
                        print(f"    └── {item}/ ({chunk_count} 个切片)")
            
            if os.path.exists(results_dir):
                print(f"  结果目录: {results_dir}")
                for item in os.listdir(results_dir):
                    item_path = os.path.join(results_dir, item)
                    if os.path.isdir(item_path):
                        result_count = len([f for f in os.listdir(item_path) if f.endswith('.json')])
                        print(f"    └── {item}/ ({result_count} 个结果文件)")
            
            # 检查最终输出文件
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    final_questions = json.load(f)
                print(f"  📊 最终输出: {len(final_questions)} 道题目")
                
                # 显示前几道题目作为样例
                for i, q in enumerate(final_questions[:3]):
                    print(f"    题目 {i+1}: {q.get('content', 'N/A')[:60]}...")
            
        else:
            print(f"❌ 测试文件不存在: {test_json_file}")
            print("请确保有一个测试用的JSON文件")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")

async def test_small_file():
    """测试小文件（不需要切分）的处理"""
    print("\n=== 测试小文件处理 ===")
    
    # 创建一个小的测试JSON文件
    small_test_data = [
        {"text": "1. 中华人民共和国的国体是什么？\nA. 人民民主专政\nB. 人民代表大会制\nC. 多党合作制\nD. 民族区域自治制", "type": "text"},
        {"text": "2. 【判断】中华人民共和国是社会主义国家。", "type": "text"},
        {"text": "3. 【多选】以下哪些是我国的基本制度？\nA. 人民代表大会制度\nB. 中国共产党领导的多党合作和政治协商制度\nC. 民族区域自治制度\nD. 基层群众自治制度", "type": "text"}
    ]
    
    small_test_file = "small_test.json"
    with open(small_test_file, 'w', encoding='utf-8') as f:
        json.dump(small_test_data, f, ensure_ascii=False, indent=2)
    
    try:
        api_key = os.getenv("SILICONFLOW_API_KEY")
        converter = PDF2QuestionConverter(api_key)
        
        output_dir = "test_small_output"
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = await converter.convert_single_file(
            small_test_file, 
            output_dir
        )
        
        print(f"✅ 小文件测试完成，输出文件: {output_file}")
        
        # 检查是否跳过了切分
        chunks_dir = os.path.join(output_dir, "切片")
        if not os.path.exists(chunks_dir) or not os.listdir(chunks_dir):
            print("✅ 确认：小文件跳过了切分步骤")
        else:
            print("⚠️  小文件也进行了切分（可能是阈值设置问题）")
            
    except Exception as e:
        print(f"❌ 小文件测试失败: {e}")
    finally:
        # 清理测试文件
        if os.path.exists(small_test_file):
            os.remove(small_test_file)

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_chunking_functionality())
    asyncio.run(test_small_file())
    
    print("\n=== 测试完成 ===")
    print("请检查生成的目录和文件，验证功能是否正常工作。") 