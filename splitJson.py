import json
import math
import os
import argparse
from pathlib import Path

def split_json_file(input_file, output_dir):
    # 读取 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON 文件内容必须是一个列表")

    total = len(data)
    part_size = math.ceil(total / 50)

    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 分割并保存
    for i in range(50):
        part = data[i * part_size: (i + 1) * part_size]
        if not part:  # 如果分片为空，跳过
            break
        output_file = os.path.join(output_dir, f"part{i + 1}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(part, f, ensure_ascii=False, indent=2)
        print(f"已保存: {output_file}（共 {len(part)} 条）")

def split_json_with_folder(input_file, base_output_dir, max_items_per_chunk=50):
    """
    为单个JSON文件创建专门的切片文件夹，并将其切分为小块
    
    Args:
        input_file: 输入JSON文件路径
        base_output_dir: 基础输出目录（切片文件夹）
        max_items_per_chunk: 每个切片的最大条目数
    
    Returns:
        tuple: (切片文件夹路径, 切片文件列表)
    """
    # 读取 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON 文件内容必须是一个列表")

    # 创建以文件名命名的子文件夹
    file_stem = Path(input_file).stem
    chunk_folder = os.path.join(base_output_dir, file_stem)
    os.makedirs(chunk_folder, exist_ok=True)
    
    total = len(data)
    if total == 0:
        print(f"警告: {input_file} 为空，跳过切分")
        return chunk_folder, []
    
    # 计算切片数量
    num_chunks = math.ceil(total / max_items_per_chunk)
    chunk_files = []
    
    print(f"切分文件 {input_file}:")
    print(f"  总条目数: {total}")
    print(f"  每片最大条目数: {max_items_per_chunk}")
    print(f"  切片数量: {num_chunks}")
    print(f"  输出文件夹: {chunk_folder}")
    
    # 分割并保存
    for i in range(num_chunks):
        start_idx = i * max_items_per_chunk
        end_idx = min((i + 1) * max_items_per_chunk, total)
        chunk = data[start_idx:end_idx]
        
        if not chunk:  # 如果分片为空，跳过
            break
            
        # 使用4位数字编号确保正确排序
        chunk_filename = f"chunk_{i+1:04d}.json"
        chunk_path = os.path.join(chunk_folder, chunk_filename)
        
        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
            
        chunk_files.append(chunk_path)
        print(f"  已保存: {chunk_filename}（条目 {start_idx+1}-{end_idx}，共 {len(chunk)} 条）")
    
    print(f"✅ 切分完成，共生成 {len(chunk_files)} 个切片文件")
    return chunk_folder, chunk_files

def merge_json_files(chunk_files, output_file):
    """
    将多个切片文件按顺序合并成一个文件
    
    Args:
        chunk_files: 切片文件路径列表（按顺序）
        output_file: 输出文件路径
    
    Returns:
        int: 合并的总题目数
    """
    merged_data = []
    
    print(f"开始合并 {len(chunk_files)} 个切片文件...")
    
    # 确保按文件名排序
    chunk_files = sorted(chunk_files)
    
    for chunk_file in chunk_files:
        if not os.path.exists(chunk_file):
            print(f"警告: 切片文件不存在，跳过: {chunk_file}")
            continue
            
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            if isinstance(chunk_data, list):
                merged_data.extend(chunk_data)
                print(f"  合并: {os.path.basename(chunk_file)} ({len(chunk_data)} 道题目)")
            else:
                print(f"警告: 切片文件格式不正确，跳过: {chunk_file}")
                
        except Exception as e:
            print(f"错误: 读取切片文件失败: {chunk_file}, 错误: {e}")
            continue
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 保存合并结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 合并完成: {output_file} (总计 {len(merged_data)} 道题目)")
    return len(merged_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将 JSON 列表等分为三份")
    parser.add_argument("input", help="输入的 JSON 文件路径")
    parser.add_argument("output", help="输出文件夹路径")
    parser.add_argument("--max-items", type=int, default=50, help="每个切片的最大条目数")
    args = parser.parse_args()

    # 使用新的切分功能
    chunk_folder, chunk_files = split_json_with_folder(args.input, args.output, args.max_items)
    print(f"切片已保存到: {chunk_folder}")


