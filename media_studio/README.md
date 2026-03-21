# 🎬 TLS 多媒體工具工作室 (media_studio)

## 目的

阿文的多媒體素材製作工具箱。鬼卒影片、小任務、工作報告統一放在這裡。

---

## 📁 目錄結構

```
media_studio/
├── README.md           ← 本檔案
├── scripts/           ← 工具腳本
│   ├── tts.sh         ← sherpa-onnx 文字轉語音
│   ├── whisper.sh     ← openai-whisper 語音轉字幕
│   ├── gen_image.sh   ← 圖片生成
│   ├── video_frames.sh # 影片截幀
│   └── pipeline.sh     # 懶人包：腳本→音頻→字幕 一鍵完成
├── assets/           ← 素材原始檔（參考圖、字體等）
├── output/           ← 產出檔（音頻、字幕、圖片）
└── reports/          ← 工作報告
```

---

## 🎙️ TTS 文字轉語音 (sherpa-onnx)

### 基本用法

```bash
./scripts/tts.sh "要轉換的文字" output.wav
```

### 測試

```bash
./scripts/tts.sh "鬼卒上班第三天，終於學會怎麼嚇人了。" output/test.wav
```

### 需求

- runtime: `~/.openclaw/tools/sherpa-onnx-tts/runtime/bin/sherpa-onnx-offline-tts`
- model: `~/.openclaw/tools/sherpa-onnx-tts/models/zh/vits-zh-aishell3/`

---

## 🎤 Whisper 語音轉字幕 (openai-whisper)

### 基本用法

```bash
./scripts/whisper.sh audio.wav
# 輸出 .srt + .vtt + .txt 三格式
```

### 需求

- `brew install openai-whisper`
- 模型自動下載（turbo ~1.5GB）

---

## 🖼️ 圖片生成 (image_generate tool)

直接用 OpenClaw 的 image_generate 工具，輸出到 `~/openclaw/media_studio/assets/`

---

## 🎬 影片截幀 (video-frames)

```bash
./scripts/video_frames.sh video.mp4 30:00
# 從 30:00 截一幀
```

需求: ffmpeg ✅ 已安裝

---

## ⚡ 一鍵 pipeline（懶人包）

```bash
./scripts/pipeline.sh ghost_ep1 "在陰間，每個靈魂的最後一程，都由鬼卒負責引導。"
```

產出：

- `output/ghost_ep1.wav` (音頻)
- `output/ghost_ep1.srt` (字幕)
- `output/ghost_ep1.txt` (文字稿)

---

## 🚀 使用範例（鬼卒第一集）

### Step 1: 產出旁白

```bash
# 開場
./scripts/tts.sh "在陰間，每個靈魂的最後一程，都由鬼卒負責引導。" output/nar_01.wav

# 遲到
./scripts/tts.sh "但今天這位鬼卒，又遲到了。" output/nar_02.wav
```

### Step 2: 合併音頻

```bash
./scripts/merge.sh output/nar_*.wav output/nar_combined.wav
```

### Step 3: 語音轉字幕

```bash
./scripts/whisper.sh output/nar_combined.wav
```

---

## 📦 模型安裝狀態

| 工具                 | 狀態 | 路徑                                                         |
| -------------------- | ---- | ------------------------------------------------------------ |
| ffmpeg               | ✅   | /opt/homebrew/bin/ffmpeg                                     |
| sherpa-onnx runtime  | ✅   | ~/.openclaw/tools/sherpa-onnx-tts/runtime                    |
| sherpa-onnx 中文模型 | ✅   | ~/.openclaw/tools/sherpa-onnx-tts/models/zh/vits-zh-aishell3 |
| openai-whisper       | ✅   | /opt/homebrew/bin/whisper                                    |

---

## 📍 快速參考

- 桌面產出路徑: `~/Desktop/`
- Whisper 模型快取: `~/.cache/whisper/`
- 影像輸出: `~/openclaw/media/tool-image-generation/`

---

> TLS 星群資產認證 | 阿文多媒體工具箱 v1.0 | 2026-03-21
