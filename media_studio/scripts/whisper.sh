#!/bin/bash
# whisper.sh - 語音轉字幕
# 用法: ./whisper.sh audio.wav

AUDIO="$1"
if [ -z "$AUDIO" ]; then
  echo "用法: ./whisper.sh audio.wav"
  exit 1
fi

whisper "$AUDIO" \
  --model turbo \
  --language Chinese \
  --output_format all \
  --output_dir "$(dirname "$AUDIO")"
