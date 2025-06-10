import json
import sys
import argparse

def check_fields(data):
    has_empty = False
    for item in data:
        # 检查correctAnswer和explanation是否为空
        correct_answer_empty = not item.get("correctAnswer", [])
        explanation_empty = not item.get("explanation", "")
        
        if correct_answer_empty or explanation_empty:
            has_empty = True
            print("以下数据存在空字段:")
            print(f"ID: {item.get('_id', {}).get('$oid', '无ID')}")
            print(f"标题: {item.get('title', '无标题')}")
            print(f"问题内容: {item.get('content', '无内容')}")
            print(f"correctAnswer为空: {correct_answer_empty}")
            print(f"explanation为空: {explanation_empty}")
            print("完整数据:")
            print(json.dumps(item, indent=2, ensure_ascii=False))
            print("\n" + "="*50 + "\n")
    
    if not has_empty:
        print("所有数据的correctAnswer和explanation字段都已填写，没有空值。")

def main():
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='检查JSON数据中的correctAnswer和explanation字段是否为空')
    parser.add_argument('file', help='要检查的JSON文件路径')
    
    args = parser.parse_args()
    
    try:
        # 读取JSON文件
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查字段
        check_fields(data)
    
    except FileNotFoundError:
        print(f"错误：文件 {args.file} 未找到")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误：文件 {args.file} 不是有效的JSON格式")
        sys.exit(1)
    except Exception as e:
        print(f"发生未知错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
