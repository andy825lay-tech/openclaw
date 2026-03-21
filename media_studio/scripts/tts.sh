#!/bin/bash
# tts.sh - 文字轉語音（sherpa-onnx）
# 用法: ./tts.sh "文字" output.wav

TEXT="$1"
OUTPUT="$2"
MODEL_DIR="$HOME/.openclaw/tools/sherpa-onnx-tts/models/zh/vits-zh-aishell3"
RUNTIME="$HOME/.openclaw/tools/sherpa-onnx-tts/runtime/bin/sherpa-onnx-offline-tts"

if [ -z "$TEXT" ] || [ -z "$OUTPUT" ]; then
  echo "用法: ./tts.sh \"文字\" output.wav"
  exit 1
fi

$RUNTIME \
  --vits-model="$MODEL_DIR/vits-aishell3.onnx" \
  --vits-tokens="$MODEL_DIR/tokens.txt" \
  --vits-lexicon="$MODEL_DIR/lexicon.txt" \
  --output-filename="$OUTPUT" \
  "$TEXT"

echo "✅ 已產出: $OUTPUT"
