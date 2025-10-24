# Generators 生成器模块

## 功能说明

内容生成模块，负责生成图片和语音内容。

## 模块列表

### image_generator.py
- **功能**: 图片生成器（基于 OpenAI DALL-E 3）
- **职责**:
  - 使用 DALL-E 3 生成场景图片
  - 生成角色图片
  - 在图片上叠加文字
  - 图片缓存管理，避免重复生成

### tts_generator.py
- **功能**: 语音生成器（基于 Google TTS）
- **职责**:
  - 使用 Google TTS 生成中文语音
  - 为场景文本生成配音
  - 音频缓存管理

## 使用示例

```python
from src.generators.image_generator import ImageGenerator
from src.generators.tts_generator import TTSGenerator

# 图片生成
image_gen = ImageGenerator(api_key="your_openai_api_key")
image_path = image_gen.generate_scene_image("一个美丽的花园", style="anime")

# 语音生成
tts_gen = TTSGenerator()
audio_path = tts_gen.generate_speech("这是一个测试文本")
```
