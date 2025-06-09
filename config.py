"""
项目配置文件
统一管理API配置、模型参数、默认值等设置
"""

import os
from typing import Dict, List, Optional

# 尝试加载.env文件
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载.env文件中的环境变量
except ImportError:
    # 如果没有安装python-dotenv，继续使用系统环境变量
    pass

class Config:
    """项目配置类"""
    
    # === API配置 ===
    SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "YOUR_SILICONFLOW_API_KEY_HERE")
    #SILICONFLOW_API_BASE = os.getenv("SILICONFLOW_API_BASE", "https://api.siliconflow.cn/v1")
    #SILICONFLOW_MODEL_NAME = os.getenv("SILICONFLOW_MODEL_NAME", "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B")
    
    SILICONFLOW_API_BASE = os.getenv("SILICONFLOW_API_BASE", "https://api.qnaigc.com/v1")
    SILICONFLOW_MODEL_NAME = os.getenv("SILICONFLOW_MODEL_NAME", "deepseek-v3-0324")
    
    # === AI模型参数 ===
    AI_CONFIG = {
        "stream": False,
        "max_tokens": int(os.getenv("MAX_TOKENS", "8192")),
        "temperature": float(os.getenv("TEMPERATURE", "0.1")),
        "top_p": float(os.getenv("TOP_P", "0.9")),
        "response_format": {"type": "json_object"}
    }
    
    # === PDF转换配置 ===
    PDF_MODES = ["auto", "txt", "ocr"]
    DEFAULT_PDF_MODE = os.getenv("DEFAULT_PDF_MODE", "auto")
    
    # === 题目类型映射 ===
    QUESTION_TYPE_MAP = {
        "单选": "single",
        "单选题": "single", 
        "多选": "multiple",
        "多选题": "multiple",
        "判断": "true_false",
        "判断题": "true_false",
        "填空题": "fill_in_the_blank",
        "简答题": "short_answer",
        "计算题": "calculation"
    }
    
    # === 难度级别映射 ===
    DIFFICULTY_MAP = {
        "简单": "easy",
        "中等": "medium", 
        "困难": "hard"
    }
    
    # === 默认值配置 ===
    DEFAULT_VALUES = {
        "title": os.getenv("DEFAULT_TITLE", "法律刷题课"),
        "subject": os.getenv("DEFAULT_SUBJECT", "gongji"),
        "module": os.getenv("DEFAULT_MODULE", "law"),
        "subModule": "",
        "difficulty": os.getenv("DEFAULT_DIFFICULTY", "medium"),
        "tags": ["法律"],
        "isActive": True,
        "stats": {
            "totalAttempts": 0,
            "correctAttempts": 0,
            "accuracy": 0
        }
    }
    
    # === 文件路径配置 ===
    DEFAULT_OUTPUT_DIR = os.getenv("DEFAULT_OUTPUT_DIR", "./output")
    DEFAULT_TEMP_DIR = os.getenv("DEFAULT_TEMP_DIR", "temp_json")
    SUPPORTED_PDF_EXTENSIONS = [".pdf"]
    SUPPORTED_JSON_EXTENSIONS = [".json"]
    
    # === 处理限制 ===
    MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "20000"))  # 单次处理的最大文本长度，减少到20k
    MAX_QUESTIONS_PER_BATCH = int(os.getenv("MAX_QUESTIONS_PER_BATCH", "50"))  # 每批次最大题目数，减少到50
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "180.0"))  # API请求超时时间(秒)，增加到3分钟
    
    # === 网络和重试配置 ===
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "7"))  # 进一步增加到7次重试
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "5.0"))  # 增加基础延迟到5秒
    CHUNK_DELAY = float(os.getenv("CHUNK_DELAY", "8.0"))  # 增加切片间延迟到8秒
    NETWORK_ERROR_DELAY = float(os.getenv("NETWORK_ERROR_DELAY", "15.0"))  # 增加网络错误延迟到15秒
    API_WARMUP_DELAY = float(os.getenv("API_WARMUP_DELAY", "2.0"))  # 新增：API调用前预热延迟
    
    # === HTTP客户端配置 ===
    HTTP_TIMEOUT = {
        "connect": float(os.getenv("HTTP_CONNECT_TIMEOUT", "60.0")),  # 增加连接超时
        "read": float(os.getenv("HTTP_READ_TIMEOUT", "180.0")),  # 增加到180秒
        "write": float(os.getenv("HTTP_WRITE_TIMEOUT", "60.0")),  # 增加写入超时
        "pool": float(os.getenv("HTTP_POOL_TIMEOUT", "300.0"))   # 增加到300秒
    }
    
    HTTP_LIMITS = {
        "max_keepalive_connections": int(os.getenv("HTTP_MAX_KEEPALIVE", "2")),  # 减少保持连接数
        "max_connections": int(os.getenv("HTTP_MAX_CONNECTIONS", "5"))  # 减少最大连接数
    }
    
    # === 日志配置 ===
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    @classmethod
    def validate_api_key(cls) -> bool:
        """验证API密钥是否设置"""
        return (cls.SILICONFLOW_API_KEY and 
                cls.SILICONFLOW_API_KEY != "YOUR_SILICONFLOW_API_KEY_HERE")
    
    @classmethod
    def get_question_type(cls, chinese_type: str) -> str:
        """获取英文题目类型"""
        return cls.QUESTION_TYPE_MAP.get(chinese_type.strip(), "unknown")
    
    @classmethod
    def get_difficulty(cls, chinese_difficulty: str) -> str:
        """获取英文难度级别"""
        return cls.DIFFICULTY_MAP.get(chinese_difficulty.strip(), "medium")
    
    @classmethod
    def get_api_config(cls) -> Dict:
        """获取API请求配置"""
        config = cls.AI_CONFIG.copy()
        config["model"] = cls.SILICONFLOW_MODEL_NAME
        return config
    
    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """获取API请求头"""
        return {
            "Authorization": f"Bearer {cls.SILICONFLOW_API_KEY}",
            "Content-Type": "application/json"
        }
    
    @classmethod
    def print_config_summary(cls):
        """打印配置摘要（用于调试）"""
        print("=== 配置摘要 ===")
        print(f"API Base: {cls.SILICONFLOW_API_BASE}")
        print(f"Model: {cls.SILICONFLOW_MODEL_NAME}")
        print(f"API Key: {'已设置' if cls.validate_api_key() else '未设置'}")
        print(f"默认输出目录: {cls.DEFAULT_OUTPUT_DIR}")
        print(f"默认PDF模式: {cls.DEFAULT_PDF_MODE}")
        print(f"最大Token数: {cls.AI_CONFIG['max_tokens']}")
        print(f"温度: {cls.AI_CONFIG['temperature']}")

# 导出配置实例
config = Config() 
