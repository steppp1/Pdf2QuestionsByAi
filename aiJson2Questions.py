#!/usr/bin/env python3
"""
AI JSON转题目处理模块 - 修复版本
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Any

import httpx
from pydantic import BaseModel, Field, ValidationError
from bson import ObjectId

from config import config

# === 数据模型定义 ===

class RawTextInput(BaseModel):
    type: str
    text: str
    text_level: Optional[int] = None
    page_idx: Optional[int] = None

def validate_objectid(v: Any) -> ObjectId:
    """验证并转换ObjectId"""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    return ObjectId()

class MongoOption(BaseModel):
    key: str
    content: str

class MongoStats(BaseModel):
    totalAttempts: int = 0
    correctAttempts: int = 0
    accuracy: int = 0

class MongoQuestion(BaseModel):
    title: Optional[str] = ""
    content: str
    type: str
    options: Optional[List[MongoOption]] = None
    correctAnswer: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    difficulty: Optional[str] = "medium"
    subject: Optional[str] = "common_knowledge"
    module: Optional[str] = ""
    subModule: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    order: Optional[int] = 0
    isActive: bool = True
    stats: MongoStats = Field(default_factory=MongoStats)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

class MongoOutput(BaseModel):
    questions: List[MongoQuestion]

def map_type_to_english(q_type: str) -> str:
    return config.get_question_type(q_type)

def map_difficulty_to_english(difficulty: str) -> str:
    return config.get_difficulty(difficulty)

async def transform_raw_text_to_mongo_questions(raw_text_data: List[Dict]) -> List[Dict]:
    """
    使用 SiliconFlow AI 将输入的原始文本数据转换为标准化的 MongoDB 题目格式。
    """
    print(f"🔄 开始处理数据，输入 {len(raw_text_data)} 条记录")
    
    if not raw_text_data:
        print(f"  ❌ 输入数据为空")
        return []
    
    # 检查API密钥
    if not config.validate_api_key():
        raise ValueError("未设置有效的SiliconFlow API密钥，请检查环境变量 SILICONFLOW_API_KEY")
    
    headers = config.get_headers()

    # 将原始文本数据转换为格式化字符串
    formatted_input_text = "\n".join([f"{idx+1}. {item['text']}" for idx, item in enumerate(raw_text_data)])

    # 限制文本长度
    if len(formatted_input_text) > config.MAX_TEXT_LENGTH:
        print(f"警告: 输入文本过长 ({len(formatted_input_text)} 字符)，截取前 {config.MAX_TEXT_LENGTH} 字符")
        formatted_input_text = formatted_input_text[:config.MAX_TEXT_LENGTH]

    # 简化 System Prompt
    system_prompt_content = """
    你是一个题目提取专家。从文本中识别完整的题目并转换为JSON格式。

    识别规则：
    - 题目以数字开头（如"1."、"2."）
    - 题型标识：【多选】、【判断】、【单选】
    - 选项以A、B、C、D开头
    - 跳过残缺题目、页眉页脚、目录等无关内容

    输出要求：
    - 只输出标准JSON格式，不要markdown标记
    - 每个题目必须有完整的题干和选项
    - 如果没有找到完整题目，返回空数组
    - 不需要判断题目类型，程序会自动处理

    输出格式：
    {
      "questions": [
        {
          "content": "题目题干",
          "options": [
            {"key": "A", "content": "选项内容"},
            {"key": "B", "content": "选项内容"}
          ],
          "correctAnswer": ["A"],
          "explanation": "解析",
          "difficulty": "medium",
          "subject": "gongji",
          "module": "law",
          "tags": ["法律"],
          "isActive": true
        }
      ]
    }
    """

    # 简化 User Prompt
    user_prompt_content = f"""
请从以下文本中提取完整的题目。只处理有明确题干和选项的题目，跳过残缺内容。

文本内容：
{formatted_input_text}

要求：
1. 识别完整题目（有题干+选项）
2. 推断正确答案和解析
3. 不需要判断题目类型，程序会自动处理
4. 只输出纯JSON格式，不要markdown
5. 没有题目时返回空数组

直接输出JSON：
    """

    messages = [
        {"role": "system", "content": system_prompt_content},
        {"role": "user", "content": user_prompt_content}
    ]

    # 获取API配置
    api_config = config.get_api_config()
    data = {
        "messages": messages,
        **api_config
    }

    # API预热延迟（给网络连接一些建立时间）
    print(f"  ⏳ API预热延迟 {config.API_WARMUP_DELAY} 秒...")
    await asyncio.sleep(config.API_WARMUP_DELAY)
    
    # 重试机制
    max_retries = config.MAX_RETRIES
    retry_delay = config.RETRY_DELAY
    generated_content = None
    
    for attempt in range(max_retries):
        try:
            timeout = httpx.Timeout(**config.HTTP_TIMEOUT)
            # 禁用连接池可以避免一些连接复用导致的ReadError
            limits = httpx.Limits(max_keepalive_connections=0, max_connections=1)
            
            async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
                print(f"  📡 API调用 (尝试 {attempt + 1}/{max_retries})...")
                
                response = await client.post(
                    f"{config.SILICONFLOW_API_BASE}/chat/completions",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                response_json = response.json()

                generated_content = response_json['choices'][0]['message']['content']
                print(f"  ✅ API调用成功")
                break  # 成功则跳出重试循环
                    
        except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
            error_type = type(e).__name__
            print(f"  ⚠️  网络连接错误 (尝试 {attempt + 1}/{max_retries}): {error_type}")
            print(f"  🌐 这通常是网络连接问题，而非数据格式问题")
            if attempt < max_retries - 1:
                # 对ReadError使用更长的延迟
                if error_type == "ReadError":
                    wait_time = retry_delay * (2 ** attempt) + config.NETWORK_ERROR_DELAY
                    print(f"  🔗 ReadError检测到，使用扩展延迟")
                else:
                    wait_time = retry_delay * (2 ** attempt)
                print(f"  ⏳ 等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
            else:
                print(f"  ❌ 达到最大重试次数，网络连接持续失败")
                raise
                        
        except httpx.HTTPStatusError as e:
            print(f"  ❌ HTTP状态错误: {e.response.status_code}")
            if e.response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt) + 5
                    print(f"  ⏳ API频率限制，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            else:
                raise
                    
        except Exception as e:
            print(f"  ⚠️  其他错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise

    # 检查是否成功获得响应
    if generated_content is None:
        print(f"  ❌ 所有重试均失败，无法获得API响应")
        return []

    # 清理AI返回的内容
    content = generated_content.strip()
    
    # 移除markdown标记
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    
    if content.endswith('```'):
        content = content[:-3]
    
    content = content.strip()
    
    # 处理多行markdown格式
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('```') and line != 'json':
            cleaned_lines.append(line)
    
    if cleaned_lines:
        content = '\n'.join(cleaned_lines)
    
    content = content.strip()
    
    # 检查内容是否为空
    if not content:
        print(f"  ⚠️  警告: AI返回的内容为空")
        return []

    # 调试：显示清理后的内容
    print(f"  📝 清理后的响应内容 ({len(content)} 字符): {content[:500]}...")

    # 解析JSON
    try:
        transformed_data = json.loads(content)
        print(f"  ✅ JSON解析成功")
    except json.JSONDecodeError as json_err:
        print(f"  ❌ 数据格式错误 - JSON解析失败: {json_err}")
        print(f"  原始内容: {content}")
        return []
    
    # 验证数据结构并获取questions数组
    if "questions" in transformed_data:
        questions_data = transformed_data["questions"]
        print(f"  📊 找到questions字段，包含 {len(questions_data)} 个项目")
        
        # 检查questions字段是否为数组
        if not isinstance(questions_data, list):
            print(f"  ❌ 数据格式错误 - questions字段不是数组类型")
            return []
    else:
        questions_data = transformed_data if isinstance(transformed_data, list) else []
        print(f"  📊 未找到questions字段，使用原始数据: {len(questions_data)} 个项目")
        
        if not isinstance(questions_data, list):
            print(f"  ❌ 数据格式错误 - 返回数据不是数组类型")
            return []

    if not questions_data:
        print(f"  ⚠️  警告: AI返回了空的题目数据")
        return []
    
    # 验证题目数据基本结构
    valid_questions = []
    for i, q_data in enumerate(questions_data):
        if not isinstance(q_data, dict):
            print(f"  ⚠️  数据格式警告: 第{i+1}题不是字典类型，跳过")
            continue
            
        if "content" not in q_data or not q_data["content"]:
            print(f"  ⚠️  数据格式警告: 第{i+1}题缺少题目内容，跳过")
            continue
            
        valid_questions.append(q_data)
    
    questions_data = valid_questions
    print(f"  📋 数据验证完成，有效题目: {len(questions_data)} 个")

    # 验证和处理题目数据
    validated_questions = []
    for q_data in questions_data:
        try:
            # 处理时间字段
            if "createdAt" in q_data and isinstance(q_data["createdAt"], str):
                try:
                    q_data["createdAt"] = datetime.fromisoformat(q_data["createdAt"].replace('Z', '+00:00'))
                except:
                    q_data["createdAt"] = datetime.utcnow()
            else:
                q_data["createdAt"] = datetime.utcnow()
                
            if "updatedAt" in q_data and isinstance(q_data["updatedAt"], str):
                try:
                    q_data["updatedAt"] = datetime.fromisoformat(q_data["updatedAt"].replace('Z', '+00:00'))
                except:
                    q_data["updatedAt"] = datetime.utcnow()
            else:
                q_data["updatedAt"] = datetime.utcnow()

            # 确保correctAnswer是列表
            if "correctAnswer" in q_data and not isinstance(q_data["correctAnswer"], list):
                if isinstance(q_data["correctAnswer"], str):
                    q_data["correctAnswer"] = [q_data["correctAnswer"]]
                else:
                    q_data["correctAnswer"] = []

            # 转换类型和难度
            if "type" in q_data:
                q_data["type"] = map_type_to_english(q_data["type"])
            if "difficulty" in q_data:
                q_data["difficulty"] = map_difficulty_to_english(q_data["difficulty"])
            
            # 智能处理题目类型识别和判断题选项补全 - 新版本
            if "content" in q_data:
                content_text = q_data["content"]
                
                # 处理判断题：检测并补全选项
                is_judgment_question = "【判断】" in content_text
                if is_judgment_question:
                    # 确保判断题有正确/错误选项
                    if "options" not in q_data or not q_data["options"]:
                        q_data["options"] = []
                    
                    # 检查是否已有正确/错误选项
                    has_correct_option = any("正确" in opt.get("content", "") for opt in q_data["options"])
                    has_wrong_option = any("错误" in opt.get("content", "") for opt in q_data["options"])
                    
                    if not has_correct_option or not has_wrong_option:
                        # 重新构建标准判断题选项
                        q_data["options"] = [
                            {"key": "A", "content": "正确"},
                            {"key": "B", "content": "错误"}
                        ]
                        print(f"  💡 自动补全判断题选项")
                
                # 根据题目特征和正确答案数量判断题目类型
                if "【多选】" in content_text:
                    q_data["type"] = "multiple"
                else:
                    # 根据正确答案数量判断题目类型
                    correct_answers = q_data.get("correctAnswer", [])
                    if len(correct_answers) > 1:
                        q_data["type"] = "multiple"
                    else:
                        # 单个答案或无答案时统一为single（包括判断题）
                        q_data["type"] = "single"
                        
                        # 如果没有选项，设为简答题
                        if not q_data.get("options"):
                            q_data["type"] = "short_answer"
            
            # 处理选项字段
            if q_data.get("type") in ["fill_in_the_blank", "short_answer"]:
                q_data["options"] = None
                if "correctAnswer" in q_data and not q_data["correctAnswer"]:
                    print(f"警告: 题目 {q_data.get('content', '未知')[:50]}... 缺少正确答案。")

            # 使用默认值
            defaults = config.DEFAULT_VALUES
            for key, value in defaults.items():
                if not q_data.get(key):
                    q_data[key] = value

            # Pydantic验证
            validated_questions.append(MongoQuestion(**q_data))

        except ValidationError as e:
            print(f"Pydantic验证失败，跳过该题目: {e}\n问题数据: {q_data}")
            continue
        except Exception as e:
            print(f"处理单个题目时发生错误: {e}\n问题数据: {q_data}")
            continue

    # 转换为最终格式（符合MongoDB格式）
    final_output_questions = []
    for i, q_obj in enumerate(validated_questions):
        q_dict = q_obj.model_dump(mode='json', exclude_none=True)
        
        # 生成MongoDB格式的ObjectId
        q_dict["_id"] = {"$oid": str(ObjectId())}
        
        # 转换时间格式为MongoDB扩展JSON格式（使用+08:00时区）
        if "createdAt" in q_dict:
            if isinstance(q_dict["createdAt"], datetime):
                # 处理datetime对象，使用+08:00代替Z
                q_dict["createdAt"] = {"$date": q_dict["createdAt"].isoformat(timespec='milliseconds') + "+08:00"}
            elif isinstance(q_dict["createdAt"], str):
                # 处理字符串
                time_str = q_dict["createdAt"]
                # 移除现有的Z或时区，替换为+08:00
                if 'Z' in time_str:
                    time_str = time_str.replace('Z', '+08:00')
                elif '+' in time_str:
                    # 如果已有其他时区，替换为+08:00
                    time_str = time_str.split('+')[0] + '+08:00'
                else:
                    # 如果没有时区信息，添加+08:00
                    time_str += '+08:00'
                q_dict["createdAt"] = {"$date": time_str}

        if "updatedAt" in q_dict:
            if isinstance(q_dict["updatedAt"], datetime):
                # 处理datetime对象，使用+08:00代替Z
                q_dict["updatedAt"] = {"$date": q_dict["updatedAt"].isoformat(timespec='milliseconds') + "+08:00"}
            elif isinstance(q_dict["updatedAt"], str):
                # 处理字符串
                time_str = q_dict["updatedAt"]
                # 移除现有的Z或时区，替换为+08:00
                if 'Z' in time_str:
                    time_str = time_str.replace('Z', '+08:00')
                elif '+' in time_str:
                    # 如果已有其他时区，替换为+08:00
                    time_str = time_str.split('+')[0] + '+08:00'
                else:
                    # 如果没有时区信息，添加+08:00
                    time_str += '+08:00'
                q_dict["updatedAt"] = {"$date": time_str}
            
        # 处理选项格式（也使用MongoDB ObjectId格式）
        if "options" in q_dict and q_dict["options"] is not None:
            for opt in q_dict["options"]:
                if "key" not in opt and "label" in opt:
                    opt["key"] = opt.pop("label")
                opt["_id"] = {"$oid": str(ObjectId())}
        
        # 处理stats字段，确保accuracy是整数
        if "stats" in q_dict and q_dict["stats"]:
            if "accuracy" in q_dict["stats"]:
                q_dict["stats"]["accuracy"] = int(q_dict["stats"]["accuracy"])
        
        # 设置题目顺序
        q_dict["order"] = i
            
        final_output_questions.append(q_dict)
    
    print(f"  🎯 最终处理完成，返回 {len(final_output_questions)} 道题目")
    return final_output_questions

if __name__ == "__main__":
    print("这是AI JSON转题目处理模块 - 修复版本") 