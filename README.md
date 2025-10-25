# 小说转动漫生成器

自动根据小说生成动漫，包含图片、文字和语音配音。

## 功能特点

- 🤖 **智能 AI 分析**：使用 DeepSeek AI 深度分析小说文本，提取场景、角色、对话和叙述
- ✨ 自动解析小说章节和段落
- 👥 智能提取小说角色并保持角色一致性
- 🎭 **角色立绘生成**：为每个主要角色生成稳定的外观设定和立绘
- 🎬 **多镜头分镜**：对每一幕剧情生成 3-5 个不同角度的场景图片（特写、中景、全景等）
- 🎨 使用 AI 生成场景图片（支持七牛 Gemini 和 OpenAI DALL-E 3）
- 🗣️ 自动生成中文语音配音（Google TTS）
- 🎥 **视频生成**：支持将场景图片转换为视频（可选）
- 📝 图文结合，文字叠加在图片上
- 💾 自动缓存已生成的图片和音频

## 安装依赖

```bash
pip3 install -r requirements.txt
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 在 `.env` 中填入你的 OpenAI API Key：

```
OPENAI_API_KEY=your_openai_api_key_here
```

## 使用方法

### Web 界面（推荐）

启动 Web 服务器：

```bash
python3 web_app.py
```

然后在浏览器中打开 `http://localhost:5000`

Web 界面功能：
- 📤 上传小说文件
- ⚙️ 配置 API Key 和场景数量
- 📊 实时查看生成进度
- 🎬 在线播放动漫场景
- 🎵 支持音频自动播放和手动控制
- 🔊 音量调节
- ⏮⏭ 场景前后导航

### 命令行用法

#### 基本用法

```bash
python3 anime_generator.py 你的小说.txt
```

#### 限制场景数量

```bash
python3 anime_generator.py 你的小说.txt --max-scenes 10
```

#### 直接传入 API Key

```bash
python3 anime_generator.py 你的小说.txt --api-key sk-xxxxx
```

## 小说格式要求

小说文本应该是纯文本格式（.txt），支持以下章节标题格式：

- 第一章 XXX
- 第1章 XXX
- 第一回 XXX
- 第001节 XXX

如果没有章节标题，将把整个文本作为一个章节处理。

## 输出结构

### 传统模式输出

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

### AI 分镜模式输出

```
output_scenes/
  scene_0000/
    shot_00.png     # 第一个分镜镜头（例如：特写）
    shot_01.png     # 第二个分镜镜头（例如：中景）
    shot_02.png     # 第三个分镜镜头（例如：全景）
    shot_03.png     # 第四个分镜镜头（例如：过肩镜头）
    narration.mp3   # 语音配音
    metadata.json   # 场景元数据（包含所有镜头信息）
  scene_0001/
    ...
image_cache/
  char_*.png        # 角色立绘缓存
  shot_*.png        # 分镜图片缓存
anime_output/
  project_metadata.json  # 整个项目的元数据
```

## 工作原理（第三版优化流程）

### 第一阶段：AI 文本分析
- 使用 **DeepSeek AI** 模型深度分析小说文本
- 提取结构化信息：
  - **场景 (Scene)**：场景描述、地点、时间
  - **人物 (Characters)**：角色名称、外貌、性格特征
  - **对话 (Dialogues)**：角色对话内容
  - **叙述 (Narration)**：旁白和描述性文本
  - **分镜脚本 (Storyboard)**：为每个场景生成 3-5 个不同镜头描述

### 第二阶段：角色立绘生成
- 根据 AI 分析的角色信息生成稳定的外观设定
- 为每个角色生成「角色立绘」（character portrait）
- 确保角色在所有场景中保持一致的外观

### 第三阶段：多镜头场景生成
- 根据 AI 分析的剧情信息和分镜脚本生成对应画面
- 为每一幕剧情生成 3-5 张不同角度的场景图片
- 支持多种镜头类型：特写、中景、全景、过肩镜头等
- 结合角色立绘信息，确保场景中角色准确呈现
- 生成的多张图片可直接作为分镜素材使用
- 将文字叠加到图片上
- 使用 gTTS 生成语音配音

## 核心模块

- `novel_analyzer.py` - **AI 小说分析器（使用 DeepSeek AI）**
- `novel_parser.py` - 小说解析器（传统模式）
- `character_manager.py` - 角色管理器
- `image_generator.py` - 图片生成器（支持七牛 Gemini 和 OpenAI DALL-E 3）
- `tts_generator.py` - 语音生成器（基于 Google TTS）
- `video_generator.py` - 视频生成器（可选）
- `scene_composer.py` - 场景组合器（支持多镜头分镜生成）
- `anime_generator.py` - 主程序和命令行接口
- `web_app.py` - Flask Web 服务器
- `templates/` - HTML 模板文件
- `static/` - CSS 和 JavaScript 静态资源

## 注意事项

- 使用 OpenAI API 会产生费用，DALL-E 3 的价格为 $0.040 per image (1024×1024)
- 建议首次使用时设置 `--max-scenes` 限制场景数量，避免产生过多费用
- 生成的图片和音频会自动缓存，重复运行不会重复生成
- 角色一致性通过提示词工程和种子值实现，但 DALL-E 3 可能仍会产生一定变化

## 示例

假设你有一个小说文件 `三体.txt`：

```bash
python3 anime_generator.py 三体.txt --max-scenes 5
```

这将生成前 5 个场景的动漫内容。

## 系统要求

- Python 3.8+
- OpenAI API Key
- 网络连接（用于调用 API）

## 许可

MIT License
