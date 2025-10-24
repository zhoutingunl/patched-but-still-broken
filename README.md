# 小说转动漫生成器

自动根据小说生成动漫，包含图片、文字和语音配音。

## 功能特点

- ✨ 自动解析小说章节和段落
- 👥 智能提取小说角色并保持角色一致性
- 🎨 使用 AI 生成场景图片（DALL-E 3）
- 🗣️ 自动生成中文语音配音（Google TTS）
- 📝 图文结合，文字叠加在图片上
- 💾 自动缓存已生成的图片和音频

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 在 `.env` 中填入你的 OpenAI API Key：

```
OPENAI_API_KEY=your_openai_api_key_here
```

## 使用方法

### 基本用法

```bash
python main.py 你的小说.txt
```

### 限制场景数量

```bash
python main.py 你的小说.txt --max-scenes 10
```

### 直接传入 API Key

```bash
python main.py 你的小说.txt --api-key sk-xxxxx
```

## 小说格式要求

小说文本应该是纯文本格式（.txt），支持以下章节标题格式：

- 第一章 XXX
- 第1章 XXX
- 第一回 XXX
- 第001节 XXX

如果没有章节标题，将把整个文本作为一个章节处理。

## 输出结构

生成的动漫内容保存在以下目录结构中：

```
output_scenes/
  scene_0000/
    scene.png       # 带文字叠加的场景图片
    narration.mp3   # 语音配音
    metadata.json   # 场景元数据
  scene_0001/
    ...
anime_output/
  project_metadata.json  # 整个项目的元数据
```

## 工作原理

1. **小说解析**：使用正则表达式解析章节和段落
2. **角色提取**：基于词频分析提取主要角色（出现3次以上）
3. **角色管理**：为每个角色分配唯一的种子值，确保生成的图片中角色外观一致
4. **场景生成**：
   - 为每个段落生成对应的场景图片
   - 识别段落中出现的角色
   - 使用 DALL-E 3 生成场景图片
   - 将文字叠加到图片上
   - 使用 gTTS 生成语音配音

## 项目结构

```
src/
├── core/               # 核心业务逻辑
│   ├── anime_generator.py    # 主程序和命令行接口
│   ├── scene_composer.py     # 场景组合器
│   └── README.md             # 模块说明
├── parsers/            # 文本解析模块
│   ├── novel_parser.py       # 小说解析器
│   └── README.md             # 模块说明
├── generators/         # 内容生成模块
│   ├── image_generator.py    # 图片生成器（DALL-E 3）
│   ├── tts_generator.py      # 语音生成器（Google TTS）
│   └── README.md             # 模块说明
└── managers/           # 管理模块
    ├── character_manager.py  # 角色管理器
    └── README.md             # 模块说明
examples/               # 示例文件
    ├── example_novel.txt     # 示例小说
    └── README.md             # 使用说明
main.py                 # 程序入口
```

## 核心模块

- **core** - 核心业务逻辑，包含主程序和场景组合功能
- **parsers** - 文本解析模块，负责解析小说章节和段落
- **generators** - 内容生成模块，负责生成图片和语音
- **managers** - 管理模块，负责角色信息管理

详细说明请查看各模块目录下的 README.md 文件。

## 注意事项

- 使用 OpenAI API 会产生费用，DALL-E 3 的价格为 $0.040 per image (1024×1024)
- 建议首次使用时设置 `--max-scenes` 限制场景数量，避免产生过多费用
- 生成的图片和音频会自动缓存，重复运行不会重复生成
- 角色一致性通过提示词工程和种子值实现，但 DALL-E 3 可能仍会产生一定变化

## 示例

假设你有一个小说文件 `三体.txt`：

```bash
python main.py 三体.txt --max-scenes 5
```

这将生成前 5 个场景的动漫内容。

或使用项目自带的示例小说：

```bash
python main.py examples/example_novel.txt --max-scenes 3
```

## 系统要求

- Python 3.8+
- OpenAI API Key
- 网络连接（用于调用 API）

## 许可

MIT License
