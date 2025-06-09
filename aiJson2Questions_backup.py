import os
import json
import httpx
import asyncio
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError, BeforeValidator
from typing import List, Dict, Union, Any, Optional
from bson import ObjectId # 用于模拟MongoDB ObjectId的类型
from config import config

#pip install httpx pydantic pymongo==4.0.0

# --- 使用配置模块中的API配置 ---
SILICONFLOW_API_KEY = config.SILICONFLOW_API_KEY
SILICONFLOW_MODEL_NAME = config.SILICONFLOW_MODEL_NAME
SILICONFLOW_API_BASE = config.SILICONFLOW_API_BASE

# --- 假设的原始输入格式 (文本流中的每行是一个字典) ---
class RawTextInput(BaseModel):
    type: str
    text: str
    text_level: Optional[int] = None
    page_idx: Optional[int] = None
    # ... 其他可能的字段


# --- MongoDB 题目数据输出结构 ---

# MongoDB _id 类型，这里我们只在Pydantic中做个占位，实际应该由MongoDB驱动生成
# 但为了演示LLM可能返回的结构，我们将其定义为str，并在后处理中转换为ObjectId
def validate_objectid(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        try:
            return ObjectId(v)
        except Exception:
            pass # Allow fallback to default_factory if string is not a valid ObjectId
    return ObjectId() # Default to a new ObjectId if validation fails

class MongoOption(BaseModel):
    key: str # AI返回的是key字段，不需要别名
    content: str
    # _id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id") # 实际由MongoDB驱动生成

class MongoStats(BaseModel):
    totalAttempts: int = 0
    correctAttempts: int = 0
    accuracy: float = 0.0

class MongoQuestion(BaseModel):
    # _id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id",
    #                                  description="MongoDB ObjectId，通常由MongoDB自动生成") # 实际由MongoDB驱动生成
    title: Optional[str] = "" # 根据输入文本推断，或者由LLM根据上下文生成
    content: str # AI返回的是content字段，不需要别名
    type: str # single, multiple, true_false, fill_in_the_blank, short_answer, calculation
    options: Optional[List[MongoOption]] = None
    correctAnswer: List[str] = Field(default_factory=list) # 统一为数组
    explanation: Optional[str] = None
    difficulty: Optional[str] = "medium" # 默认值
    subject: Optional[str] = "common_knowledge" # 默认值，根据试卷内容调整
    module: Optional[str] = "" # 默认值
    subModule: Optional[str] = "" # 默认值
    tags: List[str] = Field(default_factory=list) # 默认空列表
    order: Optional[int] = 0 # 题目顺序
    isActive: bool = True
    stats: MongoStats = Field(default_factory=MongoStats)
    createdAt: datetime = Field(default_factory=datetime.utcnow) # 自动生成 UTC 时间
    updatedAt: datetime = Field(default_factory=datetime.utcnow) # 自动生成 UTC 时间
    # __v: Optional[int] = 0 # 通常由MongoDB自动生成

class MongoOutput(BaseModel):
    questions: List[MongoQuestion] # LLM 应该返回一个包含这些题目的列表

# --- 辅助函数：将中文类型和难度转换为英文小写 (可扩展) ---
def map_type_to_english(q_type: str) -> str:
    return config.get_question_type(q_type)

def map_difficulty_to_english(difficulty: str) -> str:
    return config.get_difficulty(difficulty)


# --- 主要转换函数 ---
async def transform_raw_text_to_mongo_questions(raw_text_data: List[Dict]) -> List[Dict]:
    """
    使用 SiliconFlow AI 将输入的原始文本数据转换为标准化的 MongoDB 题目格式。
    """
    # 检查API密钥
    if not config.validate_api_key():
        raise ValueError("未设置有效的SiliconFlow API密钥，请检查环境变量 SILICONFLOW_API_KEY")
    
    headers = config.get_headers()

    # 将原始文本数据转换为 LLM 更容易理解的格式
    # 我们可以简单地将所有文本合并为一个大字符串，或者按行发送
    # 对于你的例子，每个键值对都是一行，我们可以直接使用原始字典的字符串表示
    formatted_input_text = "\n".join([f"{idx+1}. {item['text']}" for idx, item in enumerate(raw_text_data)])

    # 限制文本长度
    if len(formatted_input_text) > config.MAX_TEXT_LENGTH:
        print(f"警告: 输入文本过长 ({len(formatted_input_text)} 字符)，截取前 {config.MAX_TEXT_LENGTH} 字符")
        formatted_input_text = formatted_input_text[:config.MAX_TEXT_LENGTH]

    # --- 1. 简化 System Prompt：提高处理效率和可靠性 ---
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

    输出格式：
    {
      "questions": [
        {
          "content": "题目题干",
          "type": "single",
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

    # --- 2. 简化 User Prompt：提高处理成功率 ---
    user_prompt_content = f"""
请从以下文本中提取完整的题目。只处理有明确题干和选项的题目，跳过残缺内容。

文本内容：
{formatted_input_text}

要求：
1. 识别完整题目（有题干+选项）
2. 推断正确答案和解析
3. 确定题目类型（单选/多选/判断）
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

        # 添加重试机制
    max_retries = config.MAX_RETRIES
    retry_delay = config.RETRY_DELAY
    generated_content = None
    
    for attempt in range(max_retries):
        try:
            # 增加超时时间和连接池配置
            timeout = httpx.Timeout(**config.HTTP_TIMEOUT)
            
            # 配置连接限制
            limits = httpx.Limits(**config.HTTP_LIMITS)
            
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
            print(f"  ⚠️  网络错误 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # 指数退避
                print(f"  ⏳ 等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
                continue
            else:
                print(f"  ❌ 达到最大重试次数，放弃该请求")
                raise
                        
        except httpx.HTTPStatusError as e:
            print(f"  ❌ HTTP状态错误: {e.response.status_code}")
            if e.response.status_code == 429:  # 频率限制
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt) + 5  # 频率限制时额外等待
                    print(f"  ⏳ API频率限制，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue
            raise
                    
        except Exception as e:
            print(f"  ⚠️  其他错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            else:
                raise

    # 检查是否成功获得响应
    if generated_content is None:
        print(f"  ❌ 所有重试均失败，无法获得API响应")
        return []

    # 在成功获得API响应后处理内容
    # 清理AI返回的内容，移除可能的markdown标记
            content = generated_content.strip()
            
            # 更robust的markdown清理
            # 移除开头的markdown标记
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            
            # 移除结尾的markdown标记
            if content.endswith('```'):
                content = content[:-3]
            
            # 移除可能的其他格式标记
            content = content.strip()
            
            # 处理可能的多行markdown格式
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('```') and line != 'json':
                    cleaned_lines.append(line)
            
            if cleaned_lines:
                content = '\n'.join(cleaned_lines)
            
            # 最终清理
            content = content.strip()
            
            # 确保内容不为空
            if not content:
                print(f"  ⚠️  警告: AI返回的内容为空")
                return []

            # 调试：显示清理后的内容
            print(f"  📝 清理后的响应内容 ({len(content)} 字符): {content[:500]}...")

            # 解析 LLM 返回的 JSON 字符串
            try:
                transformed_data = json.loads(content)
                print(f"  ✅ JSON解析成功")
            except json.JSONDecodeError as json_err:
                print(f"  ❌ JSON解析失败: {json_err}")
                print(f"  原始内容: {content}")
                return []
            
            # 确保返回的是questions数组
            if "questions" in transformed_data:
                questions_data = transformed_data["questions"]
                print(f"  📊 找到questions字段，包含 {len(questions_data)} 个项目")
            else:
                questions_data = transformed_data if isinstance(transformed_data, list) else []
                print(f"  📊 未找到questions字段，使用原始数据: {len(questions_data)} 个项目")

            if not questions_data:
                print(f"  ⚠️  警告: 没有找到任何题目数据")
                return []

            validated_questions = []
            for q_data in questions_data:
                try:
                    # 在 Pydantic 验证前进行必要的后处理，因为 LLM 生成的可能不完全符合 datetime 或 ObjectId
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

                    # 确保 correctAnswer 字段是列表
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
                    
                    # 智能处理题目类型识别
                    if "content" in q_data:
                        content = q_data["content"]
                        if "【多选】" in content:
                            q_data["type"] = "multiple"
                        elif "【判断】" in content:
                            q_data["type"] = "true_false"
                        elif "【单选】" in content or ("（ ）" in content and "options" in q_data and q_data["options"]):
                            q_data["type"] = "single"
                        elif not q_data.get("type"):
                            # 根据选项数量推断类型
                            if "options" in q_data and q_data["options"]:
                                if len(q_data["options"]) <= 2:
                                    q_data["type"] = "true_false"
                                else:
                                    q_data["type"] = "single"  # 默认单选
                            else:
                                q_data["type"] = "short_answer"
                    
                    # LLM 可能会省略 options 字段，如果类型是填空或简答，确保 options 为 None
                    if q_data.get("type") in ["fill_in_the_blank", "short_answer"]:
                         q_data["options"] = None
                         if "correctAnswer" in q_data and not q_data["correctAnswer"]:
                             print(f"警告: 题目 {q_data.get('content', '未知')[:50]}... 缺少正确答案。")

                    # 使用配置文件中的默认值
                    defaults = config.DEFAULT_VALUES
                    for key, value in defaults.items():
                        if not q_data.get(key):
                            q_data[key] = value

                    # Pydantic 验证
                    validated_questions.append(MongoQuestion(**q_data))

                except ValidationError as e:
                    print(f"Pydantic 验证失败，跳过该题目: {e}\n问题数据: {q_data}")
                    continue
                except Exception as e:
                    print(f"处理单个题目时发生错误: {e}\n问题数据: {q_data}")
                    continue

            # 将 Pydantic 对象转换为字典，并进行最终的数据清理和ObjectId生成
            final_output_questions = []
            for i, q_obj in enumerate(validated_questions):
                q_dict = q_obj.model_dump(mode='json', exclude_none=True)
                
                # 生成 ObjectId
                q_dict["_id"] = str(ObjectId())
                
                # 确保时间格式正确
                if isinstance(q_dict.get("createdAt"), datetime):
                    q_dict["createdAt"] = q_dict["createdAt"].isoformat(timespec='milliseconds') + 'Z'
                if isinstance(q_dict.get("updatedAt"), datetime):
                    q_dict["updatedAt"] = q_dict["updatedAt"].isoformat(timespec='milliseconds') + 'Z'
                    
                # 处理选项格式
                if "options" in q_dict and q_dict["options"] is not None:
                    for opt in q_dict["options"]:
                        if "key" not in opt and "label" in opt:
                            opt["key"] = opt.pop("label")
                        # 为每个选项生成 ObjectId
                        opt["_id"] = str(ObjectId())
                
                # 设置题目顺序
                q_dict["order"] = i
                    
                final_output_questions.append(q_dict)
            
            return final_output_questions

        except httpx.HTTPStatusError as e:
            print(f"HTTP 错误发生: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 400:
                print("可能原因：输入文本过长或格式不正确")
            elif e.response.status_code == 401:
                print("可能原因：API密钥无效")
            elif e.response.status_code == 429:
                print("可能原因：请求频率过高，建议稍后重试")
            elif e.response.status_code >= 500:
                print("可能原因：服务器错误，建议稍后重试")
            raise
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            print(f"原始响应内容: {generated_content[:500]}...")
            raise
        except httpx.TimeoutException as e:
            print(f"请求超时: {e}")
            print("建议：减少输入文本长度或增加超时时间")
            raise
        except Exception as e:
            print(f"调用硅基流动API时发生未知错误: {e}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            print(f"详细错误堆栈:\n{traceback.format_exc()}")
            raise

# --- 示例用法 ---
async def main():
    """
    示例主函数 - 演示如何使用转换功能
    """
    try:
        # 检查配置
        if not config.validate_api_key():
            print("错误: 未设置有效的SiliconFlow API密钥")
            print("请设置环境变量 SILICONFLOW_API_KEY")
            return
        
        # 从文件加载示例数据
        with open("example_exam.json", "r", encoding="utf-8") as f:
            example_raw_text_input = json.load(f)
        
        print("正在使用硅基流动API转换题目数据...")
        print(f"输入数据行数: {len(example_raw_text_input)}")
        
        # 调用 AI 进行转换
        transformed_questions = await transform_raw_text_to_mongo_questions(example_raw_text_input)
        
        print(f"\n--- 成功转换后的 MongoDB 题目数据 ---")
        print(f"转换得到 {len(transformed_questions)} 道题目")
        
        # 保存结果到文件
        output_file = "converted_questions.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transformed_questions, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到: {output_file}")
        
        # 显示前几道题目的预览
        for i, q in enumerate(transformed_questions[:3]):
            print(f"\n题目 {i+1}:")
            print(f"  标题: {q.get('title', 'N/A')}")
            print(f"  内容: {q.get('content', 'N/A')[:100]}...")
            print(f"  类型: {q.get('type', 'N/A')}")
            print(f"  选项数: {len(q.get('options', []))} 个")
            print(f"  正确答案: {q.get('correctAnswer', [])}")

    except FileNotFoundError:
        print("错误: 找不到 example_exam.json 文件，请确保文件存在")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")

if __name__ == "__main__":
    import asyncio
    # 请设置环境变量 SILICONFLOW_API_KEY
    # export SILICONFLOW_API_KEY="sk-xxxxxxxxxxxxxx"
    asyncio.run(main())