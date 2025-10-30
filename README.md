# 小说转动漫生成器

自动根据小说生成动漫，包含图片、文字和语音配音。 公网在线DEMO地址 https://n2v.qbox.net

在线DEMO 地址https://v.douyin.com/5xbGSMy6v_g  （本链接已失效，请使用 “demo视频和说明” 目录下的演示 demo 链接:  https://b23.tv/e0HENGp ） 注： 这两个链接都是 26 日晚上 12点前上传，为避免评委看错，所以今天提交说明一下。

## 功能特点

- 🤖 **智能 AI 分析**：使用 DeepSeek AI 深度分析小说文本，提取场景、角色、对话和叙述
- ✨ 自动解析小说章节和段落
- 👥 智能提取小说角色并保持角色一致性
- 🎭 **角色立绘生成**：为每个主要角色生成稳定的外观设定和立绘
- 🎨 使用 AI 生成场景图片（支持七牛 Gemini 和 OpenAI DALL-E 3）
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

### Web 界面（推荐）

启动 Web 服务器：

```bash
python web_app.py
```

然后在浏览器中打开 `http://localhost:5000`

### 📱 Android 应用

现在支持 Android 应用！查看 [android/README.md](android/README.md) 了解详细信息。

**快速开始：**

1. 启动 Flask 服务器（绑定到所有网络接口）：
   ```bash
   python web_app.py --host 0.0.0.0 --port 5000
   ```

2. 使用 Android Studio 打开 `android` 目录并运行应用

详细的构建和配置说明请查看 Android 应用的 README。

Web 界面功能：
- 📤 上传小说文件
- ⚙️ 配置 API Key 和场景数量
- 🎬 启用/禁用分镜模式（推荐启用）
- 📊 实时查看生成进度
- 🎞️ 在线播放漫画分镜
- 📷 显示镜头类型和情感基调
- 👥 显示角色信息
- 🎵 支持音频自动播放和手动控制
- 🔊 音量调节
- ⏮⏭ 分镜前后导航

### 命令行用法

#### 基本用法

```bash
python anime_generator.py 你的小说.txt
```

#### 限制场景数量

```bash
python anime_generator.py 你的小说.txt --max-scenes 10
```

#### 直接传入 API Key

```bash
python anime_generator.py 你的小说.txt --api-key sk-xxxxx
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


## 工作原理（第四版 - 分镜系统）

### 第一阶段：AI 文本分析
- 使用 **DeepSeek AI** 模型深度分析小说文本
- 提取结构化信息：
  - **场景 (Scene)**：场景描述、地点、时间
  - **人物 (Characters)**：角色名称、外貌、性格特征
  - **对话 (Dialogues)**：角色对话内容
  - **叙述 (Narration)**：旁白和描述性文本

### 第二阶段：角色设计系统
- 为每个主要角色生成详细的设计档案
- 包含：面部特征、发型、服装、配饰等详细描述
- 生成统一的「视觉关键词」确保角色一致性
- 为每个角色生成「角色立绘」（character portrait）

### 第三阶段：分镜脚本生成（新增）
- 根据情节发展智能生成漫画分镜脚本
- 为每个分镜设计合适的镜头类型：
  - **特写 (Close-up)**：聚焦角色表情
  - **中景 (Medium shot)**：展示角色动作
  - **全景 (Full shot)**：展示角色全身
  - **远景 (Long shot)**：展示场景环境
- 标注情感基调（happy/sad/tense/calm等）
- 合理分配角色对话和旁白

### 第四阶段：分镜画面生成
- 根据分镜脚本生成对应画面
- 结合角色设计档案，确保角色外观一致
- 根据镜头类型和情感基调调整画面风格
- 将文字叠加到图片上
- 使用增强的 TTS 系统生成多角色语音（支持不同音色和情感）

## 核心模块

- `novel_analyzer.py` - **AI 小说分析器（使用 DeepSeek AI）+ 角色设计系统**
- `storyboard_generator.py` - **分镜脚本生成器（新增）**
- `novel_parser.py` - 小说解析器（传统模式，已弃用）
- `character_manager.py` - 角色管理器
- `image_generator.py` - 图片生成器（支持七牛 Gemini 和 OpenAI DALL-E 3）
- `tts_generator.py` - **增强语音生成器（支持多角色音色和情感）**
- `scene_composer.py` - 场景组合器（支持分镜模式）
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
python anime_generator.py 三体.txt --max-scenes 5
```

这将生成前 5 个场景的动漫内容。

## 系统要求

- Python 3.8+
- OpenAI API Key
- 网络连接（用于调用 API）

## 许可

MIT License
