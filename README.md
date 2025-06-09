# PDF转题目转换器

一个智能的PDF文档转题目数据转换工具，使用SiliconFlow API和AI技术自动提取并结构化试题内容。

## 🚀 功能特性

- **智能PDF解析**: 使用magic-pdf工具高质量提取PDF文本内容
- **AI驱动转换**: 基于SiliconFlow API的Qwen3-8B模型智能识别和结构化题目
- **多种输入支持**: 支持PDF文件和JSON文件作为输入源
- **智能输入检测**: 自动识别输入文件类型，选择相应处理流程
- **多种题型支持**: 单选题、多选题、判断题、填空题、简答题等
- **批量处理**: 支持单文件和批量文件夹处理模式
- **实时进度显示**: 准确的进度条显示和处理状态
- **标准化输出**: 生成MongoDB兼容的结构化题目数据
- **错误恢复**: 完善的异常处理和数据验证机制
- **环境配置**: 支持.env文件和环境变量配置

## 📋 系统要求

- Python 3.7+
- SiliconFlow API密钥
- magic-pdf工具（用于PDF转换）

## 🔧 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd pdf2question
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**

**方式一：使用.env文件（推荐）**
```bash
# 复制配置模板
cp .env.example .env
# 编辑.env文件，设置你的API密钥
nano .env
```

**方式二：设置环境变量**
```bash
export SILICONFLOW_API_KEY="sk-your-api-key-here"
```

4. **安装magic-pdf工具**
```bash
# 具体安装方法请参考magic-pdf官方文档
```

## 🎯 快速开始

### 方式一：使用命令行工具

**转换单个PDF文件:**
```bash
python main.py -i 示例.pdf -o ./output
```

**转换单个JSON文件:**
```bash
python main.py -i example.json -o ./output
```

**批量转换PDF文件夹:**
```bash
python main.py -i ./pdf_folder -o ./output --batch
```

**批量转换JSON文件夹:**
```bash
python main.py -i ./json_folder -o ./output --batch
```

**指定转换模式（仅PDF）:**
```bash
python main.py -i 示例.pdf -o ./output --mode ocr
```

**指定API密钥（临时使用）:**
```bash
python main.py -i 示例.pdf -o ./output --api-key sk-xxxxx
```

### 方式二：运行示例脚本

```bash
python run_example.py
```

### 方式三：编程调用

```python
import asyncio
from main import PDF2QuestionConverter

async def convert_pdf():
    converter = PDF2QuestionConverter("your-api-key")
    result = await converter.convert_single_pdf(
        "input.pdf", 
        "./output", 
        mode="auto"
    )
    print(f"转换完成: {result}")

asyncio.run(convert_pdf())
```

## 📖 详细用法

### 命令行参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `-i, --input` | ✅ | 输入PDF文件或文件夹路径 |
| `-o, --output` | ✅ | 输出目录路径 |
| `--batch` | ❌ | 启用批量处理模式 |
| `--mode` | ❌ | PDF转换模式: auto/txt/ocr (默认: auto) |
| `--api-key` | ❌ | SiliconFlow API密钥 |
| `--temp-dir` | ❌ | 临时JSON文件目录 |

### 转换模式说明

- **auto**: 自动选择最佳转换方式
- **txt**: 直接提取文本内容
- **ocr**: 使用OCR识别图像中的文字

### 输出格式

转换后的题目数据采用MongoDB兼容格式：

```json
{
  "_id": "ObjectId",
  "title": "题目标题",
  "content": "题目内容",
  "type": "single|multiple|true_false|fill_in_the_blank|short_answer",
  "options": [
    {"key": "A", "content": "选项内容", "_id": "ObjectId"},
    {"key": "B", "content": "选项内容", "_id": "ObjectId"}
  ],
  "correctAnswer": ["A"],
  "explanation": "答案解析",
  "difficulty": "easy|medium|hard",
  "subject": "学科",
  "module": "模块",
  "subModule": "子模块",
  "tags": ["标签"],
  "order": 0,
  "isActive": true,
  "stats": {
    "totalAttempts": 0,
    "correctAttempts": 0,
    "accuracy": 0.0
  },
  "createdAt": "2025-01-27T10:00:00.000Z",
  "updatedAt": "2025-01-27T10:00:00.000Z"
}
```

## 🏗️ 项目结构

```
pdf2question/
├── main.py                 # 主程序入口
├── aiJson2Questions.py     # AI转换模块
├── convertPdf2Json.py      # PDF转JSON模块
├── config.py              # 配置管理模块
├── run_example.py          # 示例运行脚本
├── requirements.txt        # Python依赖
├── .env.example           # 环境配置模板
├── README.md              # 项目说明
├── example_exam.json      # 示例数据
└── 示例.pdf               # 示例PDF文件
```

## 🔍 工作流程

**支持两种输入模式：**

### PDF输入模式
1. **PDF解析阶段**
   - 使用magic-pdf工具提取PDF文本
   - 保持文本结构和层次信息
   - 生成中间JSON格式数据

2. **AI转换阶段**
   - 调用SiliconFlow API的Qwen3-8B模型
   - 智能识别题目边界和类型
   - 提取题干、选项和答案
   - 生成详细的解析说明

3. **数据标准化阶段**
   - Pydantic模型验证
   - 数据类型转换和清理
   - 生成MongoDB兼容格式
   - 添加时间戳和ID字段

### JSON输入模式
1. **直接AI转换阶段**
   - 跳过PDF解析步骤
   - 直接读取JSON格式的文本数据
   - 调用SiliconFlow API进行智能识别
   - 提取和结构化题目内容

2. **数据标准化阶段**
   - 与PDF模式相同的标准化处理
   - 生成相同格式的MongoDB兼容数据

## ⚙️ 配置选项

### 环境变量配置

可以通过以下方式配置项目：

1. **创建.env文件**（推荐）
2. **设置系统环境变量**
3. **命令行参数**

### 主要配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SILICONFLOW_API_KEY` | 无 | SiliconFlow API密钥（必需） |
| `SILICONFLOW_MODEL_NAME` | `Qwen/Qwen3-8B` | 使用的AI模型 |
| `DEFAULT_OUTPUT_DIR` | `./output` | 默认输出目录 |
| `DEFAULT_PDF_MODE` | `auto` | 默认PDF转换模式 |
| `MAX_TOKENS` | `8192` | AI模型最大token数 |
| `TEMPERATURE` | `0.1` | AI模型温度参数 |
| `REQUEST_TIMEOUT` | `120.0` | API请求超时时间(秒) |

完整的配置选项请参考 `.env.example` 文件。

### 模型配置

默认使用 `Qwen/Qwen3-8B` 模型，可通过环境变量修改：

```bash
export SILICONFLOW_MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
```

或在.env文件中设置：
```
SILICONFLOW_MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
```

## 🐛 常见问题

**Q: 提示API密钥错误**
A: 
1. 确保设置了正确的环境变量 `SILICONFLOW_API_KEY`
2. 检查.env文件是否存在且配置正确
3. 使用 `python run_example.py` 查看配置摘要

**Q: PDF转换失败，提示"PDF folder not found"**
A: 
1. 确保输入的PDF文件路径正确
2. 检查magic-pdf工具是否正确安装
3. 尝试使用绝对路径

**Q: AI识别准确率低**
A: 
1. 确保PDF质量良好，文字清晰
2. 尝试不同的转换模式（--mode ocr）
3. 检查输入文本是否完整

**Q: 内存占用过高**
A: 建议分批处理大量PDF文件，避免一次性处理过多文档

## 🚀 最新更新

### v2.0 (2025-01-27)
- ✅ **修复单文件转换问题**: 解决了PDF路径处理错误
- ✅ **添加.env文件支持**: 支持通过.env文件配置环境变量
- ✅ **配置管理模块**: 统一的配置管理和验证
- ✅ **改进错误处理**: 更详细的错误信息和调试输出
- ✅ **优化代码结构**: 模块化设计，提高可维护性

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [SiliconFlow API文档](https://docs.siliconflow.cn/)
- [magic-pdf项目](https://github.com/opendatalab/MinerU)
- [Pydantic文档](https://docs.pydantic.dev/)

---

**注意**: 使用本工具时请确保遵守相关的版权和隐私法规。
