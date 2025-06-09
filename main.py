#!/usr/bin/env python3
"""
PDF to Question Converter - 主程序入口
将PDF文件转换为结构化的题目数据，适用于考试题库建设

使用流程:
1. PDF -> JSON (使用magic-pdf工具)  或  直接使用JSON文件
2. JSON -> 标准化题目数据 (使用SiliconFlow AI)

支持批量处理和单文件处理模式
支持PDF文件和JSON文件作为输入
"""

import os
import sys
import json
import argparse
import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
import re

# 导入项目模块
from convertPdf2Json import ConvertPdf2Json
from aiJson2Questions import transform_raw_text_to_mongo_questions
from splitJson import split_json_with_folder, merge_json_files
from config import config

class PDF2QuestionConverter:
    """PDF到题目转换器主类"""
    
    def __init__(self, siliconflow_api_key: Optional[str] = None):
        self.api_key = siliconflow_api_key or os.getenv("SILICONFLOW_API_KEY")
        if not self.api_key or self.api_key == "YOUR_SILICONFLOW_API_KEY_HERE":
            raise ValueError("请设置环境变量 SILICONFLOW_API_KEY 或通过参数传入API密钥")
        
        # 设置环境变量以供子模块使用
        os.environ["SILICONFLOW_API_KEY"] = self.api_key
    
    def detect_input_type(self, input_path: str) -> str:
        """检测输入文件类型"""
        if os.path.isfile(input_path):
            if input_path.lower().endswith('.pdf'):
                return "pdf_file"
            elif input_path.lower().endswith('.json'):
                return "json_file"
            else:
                raise ValueError(f"不支持的文件类型: {input_path}")
        elif os.path.isdir(input_path):
            # 检查目录中的文件类型
            pdf_files = []
            json_files = []
            for root, dirs, files in os.walk(input_path):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(file)
                    elif file.lower().endswith('.json'):
                        json_files.append(file)
            
            if pdf_files and json_files:
                raise ValueError(f"目录中同时包含PDF和JSON文件，请分别处理: {input_path}")
            elif pdf_files:
                return "pdf_folder"
            elif json_files:
                return "json_folder"
            else:
                raise ValueError(f"目录中没有找到PDF或JSON文件: {input_path}")
        else:
            raise FileNotFoundError(f"输入路径不存在: {input_path}")
    
    def validate_paths(self, input_path: str, output_dir: str) -> None:
        """验证输入输出路径"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入路径不存在: {input_path}")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        print(f"输出目录: {output_dir}")
    
    def convert_single_pdf_to_json(self, pdf_file: str, json_output_dir: str, mode: str = "auto") -> List[str]:
        """单个PDF文件转JSON"""
        print(f"\n=== 第一步：PDF转JSON ===")
        print(f"输入文件: {pdf_file}")
        print(f"输出目录: {json_output_dir}")
        print(f"模式: {mode}")
        
        # 为单个文件创建临时目录结构
        temp_pdf_dir = os.path.join(json_output_dir, "temp_pdf_input")
        os.makedirs(temp_pdf_dir, exist_ok=True)
        
        # 复制PDF文件到临时目录
        temp_pdf_path = os.path.join(temp_pdf_dir, os.path.basename(pdf_file))
        shutil.copy2(pdf_file, temp_pdf_path)
        
        try:
            # 使用临时目录作为输入
            converter = ConvertPdf2Json(temp_pdf_dir, json_output_dir, mode)
            success = converter.convert()
            
            if not success:
                raise RuntimeError("PDF转换失败")
            
            # 查找生成的JSON文件
            json_files = []
            for root, dirs, files in os.walk(json_output_dir):
                for file in files:
                    if file.endswith('.json') and not root.endswith('temp_pdf_input'):
                        json_files.append(os.path.join(root, file))
            
            print(f"生成的JSON文件: {len(json_files)} 个")
            return json_files
            
        finally:
            # 清理临时PDF目录
            if os.path.exists(temp_pdf_dir):
                shutil.rmtree(temp_pdf_dir, ignore_errors=True)
    
    def convert_pdf_folder_to_json(self, pdf_folder: str, json_output_dir: str, mode: str = "auto") -> List[str]:
        """PDF文件夹转JSON"""
        print(f"\n=== 第一步：PDF转JSON ===")
        print(f"输入文件夹: {pdf_folder}")
        print(f"输出目录: {json_output_dir}")
        print(f"模式: {mode}")
        
        converter = ConvertPdf2Json(pdf_folder, json_output_dir, mode)
        success = converter.convert()
        
        if not success:
            raise RuntimeError("PDF转换失败")
        
        # 查找生成的JSON文件
        json_files = []
        for root, dirs, files in os.walk(json_output_dir):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        print(f"生成的JSON文件: {len(json_files)} 个")
        return json_files
    
    def collect_json_files(self, input_path: str) -> List[str]:
        """收集JSON文件（直接输入JSON时使用）"""
        print(f"\n=== 检测到JSON输入，跳过PDF转换步骤 ===")
        
        json_files = []
        if os.path.isfile(input_path):
            json_files = [input_path]
            print(f"单个JSON文件: {input_path}")
        elif os.path.isdir(input_path):
            for root, dirs, files in os.walk(input_path):
                for file in files:
                    if file.lower().endswith('.json'):
                        json_files.append(os.path.join(root, file))
            print(f"JSON文件夹: {input_path}")
            print(f"发现 {len(json_files)} 个JSON文件")
        
        if not json_files:
            raise ValueError("没有找到有效的JSON文件")
        
        return json_files
    
    async def convert_json_to_questions(self, json_files: List[str], output_file: str) -> List[Dict]:
        """第二步：JSON转题目数据（支持自动切分和拼合）"""
        print(f"\n=== 第二步：JSON转题目数据 ===")
        print(f"处理 {len(json_files)} 个JSON文件")
        
        all_questions = []
        
        # 创建切片和输出目录
        base_output_dir = os.path.dirname(output_file)
        chunks_base_dir = os.path.join(base_output_dir, "切片")
        results_base_dir = os.path.join(base_output_dir, "results")
        os.makedirs(chunks_base_dir, exist_ok=True)
        os.makedirs(results_base_dir, exist_ok=True)
        
        for i, json_file in enumerate(json_files, 1):
            print(f"\n处理文件 {i}/{len(json_files)}: {os.path.basename(json_file)}")
            
            try:
                # 解析JSON文件
                json_data = await self._parse_json_file(json_file)
                if not json_data:
                    continue
                
                # 检查是否需要切分
                file_questions = await self._process_json_with_chunking(
                    json_file, json_data, chunks_base_dir, results_base_dir
                )
                
                if file_questions:
                    all_questions.extend(file_questions)
                    print(f"✅ 文件 {os.path.basename(json_file)} 处理完成: {len(file_questions)} 道题目")
                else:
                    print(f"❌ 文件 {os.path.basename(json_file)} 处理失败: 无题目输出")
                    
            except Exception as e:
                print(f"错误: 处理文件 {json_file} 时发生异常: {e}")
                import traceback
                print(f"详细错误信息:\n{traceback.format_exc()}")
                continue
        
        # 保存最终结果
        print(f"\n总计转换题目: {len(all_questions)} 道")
        
        # 对题目数据进行过滤和处理
        print(f"📋 开始过滤和处理题目数据...")
        filtered_questions = []
        removed_count = 0
        processed_count = 0
        
        for question in all_questions:
            # a. 如果type不属于single、multiple，那么直接删除这个条目
            question_type = question.get("type", "")
            if question_type not in ["single", "multiple"]:
                removed_count += 1
                print(f"  ❌ 删除题目 (类型: {question_type}): {question.get('content', '未知题目')[:50]}...")
                continue
            
            # b. 如果缺乏explanation字段，那么添加上这个字段，默认为空
            if "explanation" not in question or question["explanation"] is None:
                question["explanation"] = ""
                processed_count += 1
            
            filtered_questions.append(question)
        
        print(f"  ✅ 过滤完成: 保留 {len(filtered_questions)} 道题目，删除 {removed_count} 道题目")
        print(f"  🔧 处理完成: 补充 {processed_count} 个explanation字段")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_questions, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到: {output_file}")
        print(f"最终输出: {len(filtered_questions)} 道有效题目")
        return filtered_questions
    
    async def _parse_json_file(self, json_file: str) -> List[Dict]:
        """解析JSON文件，处理各种格式问题"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 尝试修复JSON格式问题
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"原始JSON解析失败: {e}")
                print("尝试修复JSON格式...")
                
                # 尝试修复JavaScript对象格式（没有引号的键名）
                try:
                    # 修复 { type: "text" } 格式为 { "type": "text" }
                    fixed_content = re.sub(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', content)
                    # 修复省略号
                    fixed_content = re.sub(r'…\s*}', '}', fixed_content)
                    
                    # 如果是单行格式，尝试解析为数组
                    if '\n' in fixed_content and not fixed_content.strip().startswith('['):
                        # 按行分割并构建数组
                        lines = []
                        for line in fixed_content.strip().split('\n'):
                            line = line.strip()
                            if line and not line.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
                                # 跳过行号
                                try:
                                    # 尝试解析单行对象
                                    obj = json.loads(line)
                                    lines.append(obj)
                                except:
                                    continue
                            elif line.startswith('{'):
                                try:
                                    obj = json.loads(line)
                                    lines.append(obj)
                                except:
                                    continue
                        
                        if lines:
                            json_data = lines
                        else:
                            print(f"无法修复JSON格式，尝试逐行解析...")
                            json_data = self._parse_lines_manually(content)
                    else:
                        json_data = json.loads(fixed_content)
                        
                except Exception as e2:
                    print(f"JSON格式修复失败: {e2}")
                    print("尝试逐行解析...")
                    json_data = self._parse_lines_manually(content)
            
            # 标准化数据格式
            if isinstance(json_data, list):
                formatted_data = []
                for item in json_data:
                    if isinstance(item, dict) and 'text' in item:
                        formatted_data.append(item)
                    elif isinstance(item, str):
                        formatted_data.append({"text": item, "type": "text"})
                return formatted_data
            else:
                return [{"text": str(json_data), "type": "text"}]
                
        except Exception as e:
            print(f"解析JSON文件失败: {e}")
            return []
    
    async def _process_json_with_chunking(self, json_file: str, json_data: List[Dict], 
                                        chunks_base_dir: str, results_base_dir: str) -> List[Dict]:
        """处理JSON文件，如果需要则进行切分和拼合"""
        # 估算文本总长度
        total_text_length = 0
        valid_text_lines = 0
        
        for item in json_data:
            if isinstance(item, dict) and 'text' in item:
                text = item['text']
                if text and text.strip():
                    total_text_length += len(text)
                    valid_text_lines += 1
        
        print(f"  有效文本行数: {valid_text_lines}")
        print(f"  文本总长度: {total_text_length} 字符")
        
        # 决定是否需要切分
        if valid_text_lines > 50 or total_text_length > 15000:  # 需要切分
            print(f"📄 文件较大，启用切分处理模式")
            return await self._process_with_chunking(json_file, json_data, chunks_base_dir, results_base_dir)
        else:
            # 直接处理小文件
            print(f"📄 文件较小，直接处理")
            try:
                print(f"📡 正在调用AI处理文件...")
                questions = await transform_raw_text_to_mongo_questions(json_data)
                
                if questions:
                    # 验证返回数据质量
                    valid_count = 0
                    for q in questions:
                        if isinstance(q, dict) and q.get("content") and q.get("type"):
                            valid_count += 1
                    
                    print(f"📊 AI返回数据: {len(questions)} 条记录，{valid_count} 条有效")
                    print(f"✅ 文件处理完成: {valid_count} 道有效题目")
                    return questions
                else:
                    print(f"⚠️  文件处理完成但AI未返回有效题目数据")
                    print(f"💡 可能原因: 1) 网络连接问题 2) AI返回数据格式不规范 3) 文本内容无法识别为题目")
                    return []
                    
            except Exception as api_error:
                error_type = type(api_error).__name__
                print(f"❌ 文件处理失败: {error_type}")
                
                # 区分错误类型并给出不同提示
                if any(net_err in error_type for net_err in ["ReadError", "ConnectError", "TimeoutException"]):
                    print(f"🌐 网络连接错误 - 这是真正的网络问题")
                    print(f"💡 建议: 检查网络连接或API服务状态")
                elif "JSON" in str(api_error) or "格式" in str(api_error):
                    print(f"📝 数据格式错误 - AI返回的数据不符合预期格式") 
                    print(f"💡 建议: 检查AI提示词或数据处理逻辑")
                else:
                    print(f"❓ 未知错误类型")
                    
                print(f"详细错误: {str(api_error)[:200]}...")
                raise  # 重新抛出异常以便上层处理
    
    async def _process_with_chunking(self, json_file: str, json_data: List[Dict], 
                                   chunks_base_dir: str, results_base_dir: str) -> List[Dict]:
        """使用切分方式处理大文件"""
        file_stem = Path(json_file).stem
        
        # 第一步：切分JSON文件
        print(f"  🔪 正在切分文件...")
        
        # 创建临时JSON文件用于切分
        temp_json_file = os.path.join(chunks_base_dir, f"temp_{file_stem}.json")
        with open(temp_json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        try:
            # 切分文件
            chunk_folder, chunk_files = split_json_with_folder(
                temp_json_file, chunks_base_dir, max_items_per_chunk=50
            )
            
            if not chunk_files:
                print(f"  ❌ 切分失败，没有生成切片文件")
                return []
            
            # 第二步：创建结果文件夹
            result_folder = os.path.join(results_base_dir, file_stem)
            os.makedirs(result_folder, exist_ok=True)
            
            # 第三步：逐个处理切片
            print(f"  🔄 处理 {len(chunk_files)} 个切片...")
            result_files = []
            
            for j, chunk_file in enumerate(chunk_files, 1):
                chunk_name = Path(chunk_file).stem
                result_file = os.path.join(result_folder, f"{chunk_name}_result.json")
                
                print(f"    处理切片 {j}/{len(chunk_files)}: {chunk_name}")
                
                try:
                    # 加载切片数据
                    with open(chunk_file, 'r', encoding='utf-8') as f:
                        chunk_data = json.load(f)
                    
                    if not chunk_data:
                        print(f"    ⚠️  切片 {chunk_name} 为空，跳过")
                        continue
                    
                    # 处理切片
                    try:
                        print(f"    📡 正在调用AI处理切片 {chunk_name}...")
                        chunk_questions = await transform_raw_text_to_mongo_questions(chunk_data)
                        
                        if chunk_questions:
                            # 验证返回数据质量
                            valid_count = 0
                            for q in chunk_questions:
                                if isinstance(q, dict) and q.get("content") and q.get("type"):
                                    valid_count += 1
                            
                            print(f"    📊 AI返回数据: {len(chunk_questions)} 条记录，{valid_count} 条有效")
                            
                            # 保存切片结果
                            with open(result_file, 'w', encoding='utf-8') as f:
                                json.dump(chunk_questions, f, ensure_ascii=False, indent=2)
                            
                            result_files.append(result_file)
                            print(f"    ✅ 切片 {chunk_name} 处理完成: {valid_count} 道有效题目")
                        else:
                            print(f"    ⚠️  切片 {chunk_name} 处理完成但AI未返回有效题目数据")
                            print(f"    💡 可能原因: 1) 网络连接问题 2) AI返回数据格式不规范 3) 文本内容无法识别为题目")
                            
                    except Exception as api_error:
                        error_type = type(api_error).__name__
                        print(f"    ❌ 切片 {chunk_name} 处理失败: {error_type}")
                        
                        # 区分错误类型并给出不同提示
                        if any(net_err in error_type for net_err in ["ReadError", "ConnectError", "TimeoutException"]):
                            print(f"    🌐 网络连接错误 - 这是真正的网络问题")
                            print(f"    💡 建议: 检查网络连接或API服务状态")
                            await asyncio.sleep(config.NETWORK_ERROR_DELAY)  # 网络错误时额外等待
                        elif "JSON" in str(api_error) or "格式" in str(api_error):
                            print(f"    📝 数据格式错误 - AI返回的数据不符合预期格式")
                            print(f"    💡 建议: 检查AI提示词或数据处理逻辑")
                        else:
                            print(f"    ❓ 未知错误类型")
                            
                        print(f"    详细错误: {str(api_error)[:200]}...")
                        # 继续处理下一个切片
                        continue
                    
                    # 添加延迟避免API频率限制
                    if j < len(chunk_files):
                        print(f"    ⏳ 等待{config.CHUNK_DELAY}秒后处理下一个切片...")
                        await asyncio.sleep(config.CHUNK_DELAY)
                        
                except Exception as e:
                    print(f"    ❌ 处理切片 {chunk_name} 时发生未知错误: {type(e).__name__}")
                    print(f"        错误详情: {str(e)[:200]}...")
                    # 记录错误但继续处理
                    continue
            
            # 第四步：合并结果
            if result_files:
                print(f"  🔗 合并 {len(result_files)} 个结果文件...")
                
                merged_questions = []
                for result_file in sorted(result_files):
                    try:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            questions = json.load(f)
                        if isinstance(questions, list):
                            merged_questions.extend(questions)
                    except Exception as e:
                        print(f"    警告: 读取结果文件失败: {result_file}, 错误: {e}")
                        continue
                
                print(f"  ✅ 合并完成，总计 {len(merged_questions)} 道题目")
                return merged_questions
            else:
                print(f"  ❌ 没有有效的结果文件")
                return []
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_json_file):
                os.remove(temp_json_file)
    
    def _parse_lines_manually(self, content: str) -> List[Dict]:
        """手动逐行解析非标准JSON格式"""
        lines = []
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            if not line:
                continue
                
            # 跳过纯数字行号
            if line.isdigit():
                continue
            
            # 移除开头的行号（如果存在）
            # 格式如 "1\t{ type: ..."
            if '\t' in line and line.split('\t')[0].isdigit():
                line = '\t'.join(line.split('\t')[1:])
            
            # 检查是否包含对象格式
            if line.startswith('{') and ('type:' in line or 'text:' in line):
                try:
                    # 修复JavaScript对象格式
                    # 1. 替换没有引号的键名
                    fixed_line = re.sub(r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', line)
                    # 2. 处理省略号
                    fixed_line = re.sub(r',\s*…\s*}', ' }', fixed_line)
                    fixed_line = re.sub(r'…\s*}', ' }', fixed_line)
                    # 3. 处理缺少值的键
                    fixed_line = re.sub(r',\s*"[^"]*":\s*,', ',', fixed_line)
                    fixed_line = re.sub(r',\s*"[^"]*":\s*}', ' }', fixed_line)
                    
                    # 尝试解析修复后的JSON
                    obj = json.loads(fixed_line)
                    
                    # 验证必需字段
                    if 'text' in obj and obj['text'].strip():
                        # 确保有type字段
                        if 'type' not in obj:
                            obj['type'] = 'text'
                        lines.append(obj)
                        
                except Exception as parse_error:
                    # 如果JSON解析失败，尝试简单的文本提取
                    text_match = re.search(r'"text":\s*"([^"]*)"', line)
                    if not text_match:
                        text_match = re.search(r'text:\s*"([^"]*)"', line)
                    
                    if text_match:
                        text = text_match.group(1)
                        if text.strip():
                            lines.append({"type": "text", "text": text})
                    else:
                        print(f"    跳过无法解析的行 {line_num}: {line[:50]}...")
                    continue
        
        if lines:
            print(f"逐行解析成功，提取 {len(lines)} 条记录")
        
        return lines
    

    
    async def convert_single_file(self, input_file: str, output_dir: str, 
                                temp_dir: Optional[str] = None, 
                                mode: str = "auto") -> str:
        """转换单个文件（PDF或JSON）"""
        input_type = self.detect_input_type(input_file)
        print(f"开始转换文件: {input_file}")
        print(f"检测到输入类型: {input_type}")
        
        self.validate_paths(input_file, output_dir)
        
        try:
            if input_type == "pdf_file":
                # PDF文件处理流程
                if temp_dir is None:
                    temp_dir = os.path.join(output_dir, "temp_json")
                
                # 第一步：PDF转JSON
                json_files = self.convert_single_pdf_to_json(input_file, temp_dir, mode)
                
                # 清理临时文件选项
                cleanup_temp = True
                
            elif input_type == "json_file":
                # JSON文件直接处理
                json_files = self.collect_json_files(input_file)
                cleanup_temp = False
                
            else:
                raise ValueError(f"不支持的输入类型: {input_type}")
            
            # 第二步：JSON转题目
            file_stem = Path(input_file).stem
            output_file = os.path.join(output_dir, f"{file_stem}_questions.json")
            
            questions = await self.convert_json_to_questions(json_files, output_file)
            
            # 清理临时文件（仅PDF转换需要）
            if cleanup_temp and temp_dir:
                cleanup = input("是否删除临时JSON文件? (y/N): ").lower().strip()
                if cleanup in ['y', 'yes']:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        print("临时文件已清理")
            
            return output_file
            
        except Exception as e:
            print(f"转换失败: {e}")
            raise
    
    async def convert_folder(self, input_folder: str, output_dir: str,
                           mode: str = "auto") -> List[str]:
        """批量转换文件夹（PDF或JSON）"""
        input_type = self.detect_input_type(input_folder)
        print(f"开始批量转换文件夹: {input_folder}")
        print(f"检测到输入类型: {input_type}")
        
        self.validate_paths(input_folder, output_dir)
        
        try:
            if input_type == "pdf_folder":
                # PDF文件夹处理流程
                temp_dir = os.path.join(output_dir, "temp_json")
                
                # 第一步：批量PDF转JSON
                json_files = self.convert_pdf_folder_to_json(input_folder, temp_dir, mode)
                
                # 第二步：JSON转题目（按PDF分组处理）
                pdf_files = []
                for root, dirs, files in os.walk(input_folder):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            pdf_files.append(os.path.join(root, file))
                
                output_files = []
                for pdf_file in pdf_files:
                    # 找到对应的JSON文件
                    pdf_name = Path(pdf_file).stem
                    related_json_files = [f for f in json_files if pdf_name in f]
                    
                    if related_json_files:
                        output_file = os.path.join(
                            output_dir, 
                            f"{pdf_name}_questions.json"
                        )
                        
                        await self.convert_json_to_questions(related_json_files, output_file)
                        output_files.append(output_file)
                
                # 清理临时文件
                cleanup = input("是否删除临时JSON文件? (y/N): ").lower().strip()
                if cleanup in ['y', 'yes']:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        print("临时文件已清理")
                
            elif input_type == "json_folder":
                # JSON文件夹直接处理
                json_files = self.collect_json_files(input_folder)
                
                # 可以选择合并处理或分别处理
                process_type = input("批量JSON处理方式 - [1] 合并为单个输出 [2] 分别处理 (默认:1): ").strip()
                
                if process_type == "2":
                    # 分别处理每个JSON文件
                    output_files = []
                    for json_file in json_files:
                        file_name = Path(json_file).stem
                        output_file = os.path.join(output_dir, f"{file_name}_questions.json")
                        await self.convert_json_to_questions([json_file], output_file)
                        output_files.append(output_file)
                else:
                    # 合并处理
                    output_file = os.path.join(output_dir, "merged_questions.json")
                    await self.convert_json_to_questions(json_files, output_file)
                    output_files = [output_file]
            
            else:
                raise ValueError(f"不支持的输入类型: {input_type}")
            
            return output_files
            
        except Exception as e:
            print(f"批量转换失败: {e}")
            raise

    # 保持向后兼容的方法名
    async def convert_single_pdf(self, pdf_file: str, output_dir: str, 
                               temp_dir: Optional[str] = None, 
                               mode: str = "auto") -> str:
        """转换单个PDF文件（保持向后兼容）"""
        return await self.convert_single_file(pdf_file, output_dir, temp_dir, mode)
    
    async def convert_pdf_folder(self, pdf_folder: str, output_dir: str,
                               mode: str = "auto") -> List[str]:
        """批量转换PDF文件夹（保持向后兼容）"""
        return await self.convert_folder(pdf_folder, output_dir, mode)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PDF/JSON转题目转换器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 转换单个PDF文件
  python main.py -i example.pdf -o ./output
  
  # 转换单个JSON文件
  python main.py -i example.json -o ./output
  
  # 批量转换PDF文件夹
  python main.py -i ./pdf_folder -o ./output --batch
  
  # 批量转换JSON文件夹
  python main.py -i ./json_folder -o ./output --batch
  
  # 指定转换模式（仅PDF转换）
  python main.py -i example.pdf -o ./output --mode ocr
  
  # 指定API密钥
  python main.py -i example.pdf -o ./output --api-key sk-xxxxx
        """
    )
    
    parser.add_argument(
        "-i", "--input", 
        required=True,
        help="输入PDF/JSON文件或文件夹路径"
    )
    
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="输出目录路径"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（处理文件夹中的所有文件）"
    )
    
    parser.add_argument(
        "--mode",
        choices=["auto", "txt", "ocr"],
        default="auto",
        help="PDF转换模式 (默认: auto，仅对PDF文件有效)"
    )
    
    parser.add_argument(
        "--api-key",
        help="SiliconFlow API密钥（也可通过环境变量SILICONFLOW_API_KEY设置）"
    )
    
    parser.add_argument(
        "--temp-dir",
        help="临时JSON文件目录（默认在输出目录下创建temp_json）"
    )
    
    return parser.parse_args()

async def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        print("=" * 60)
        print("      PDF/JSON转题目转换器")
        print("=" * 60)
        
        # 初始化转换器
        converter = PDF2QuestionConverter(args.api_key)
        
        # 检测输入类型
        input_type = converter.detect_input_type(args.input)
        print(f"检测到输入类型: {input_type}")
        
        # 根据模式执行转换
        if args.batch:
            if not os.path.isdir(args.input):
                print("错误: 批量模式需要输入文件夹路径")
                sys.exit(1)
            
            output_files = await converter.convert_folder(
                args.input, 
                args.output, 
                args.mode
            )
            
            print(f"\n转换完成! 生成了 {len(output_files)} 个题目文件:")
            for file in output_files:
                print(f"  - {file}")
        
        else:
            if not os.path.isfile(args.input):
                print("错误: 单文件模式需要输入文件路径")
                sys.exit(1)
            
            output_file = await converter.convert_single_file(
                args.input,
                args.output,
                args.temp_dir,
                args.mode
            )
            
            print(f"\n转换完成! 题目文件: {output_file}")
        
        print("\n转换成功完成! 🎉")
        
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        sys.exit(1)
    
    # 运行主程序
    asyncio.run(main())


