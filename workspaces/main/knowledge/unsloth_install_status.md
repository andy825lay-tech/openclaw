# Unsloth 安裝狀態報告

**日期：** 2026-03-21
**執行者：** 阿研（CRO）+ 阿工（CTO）

---

## ⚠️ 關鍵發現：Unsloth 不支援 Apple Silicon MPS

**問題：** Unsloth（包含 `unsloth` 和 `unsloth-zoo`）**目前只支援 NVIDIA/AMD/Intel GPU**，**不支援 Apple Silicon 的 Metal MPS（Metal Performance Shaders）**。

```
NotImplementedError: Unsloth currently only works on NVIDIA, AMD and Intel GPUs.
```

---

## ✅ 替代方案：MLX + mlx_lm（Apple Silicon 原生方案）

**已成功使用的替代工具鏈：**

| 套件          | 版本     | 用途                       |
| ------------- | -------- | -------------------------- |
| `torch`       | 2.10.0   | PyTorch（含 MPS 支援）     |
| `mlx`         | 0.31.1   | Apple MLX 核心框架         |
| `mlx-metal`   | 0.31.1   | Metal GPU 加速             |
| `mlx-lm`      | 0.31.1   | Apple Silicon LLM 微調工具 |
| `unsloth-zoo` | 2026.3.4 | 部分功能可用（需 MPS）     |

---

## 環境驗證結果

| 項目                            | 狀態 | 備註                                        |
| ------------------------------- | ---- | ------------------------------------------- |
| Apple Silicon (M3 Ultra)        | ✅   | 60-core Metal GPU                           |
| MPS (Metal Performance Shaders) | ✅   | torch.backends.mps.is_available() = True    |
| CUDA (NVIDIA)                   | ❌   | Mac 無 NVIDIA                               |
| Python                          | ✅   | 3.14.3                                      |
| pip 環境                        | ✅   | 使用 venv (`~/.openclaw/venvs/unsloth-env`) |
| HuggingFace Hub 訪問            | ✅   | 公共模型無需 Token                          |
| 磁碟空間                        | ✅   | 926GB 總容量，508GB 可用                    |

---

## 安裝記錄

```bash
# 1. 建立虛擬環境
python3 -m venv ~/.openclaw/venvs/unsloth-env

# 2. 安裝 Unsloth（成功但 MPS 不支援）
pip install unsloth unsloth-zoo  # ✅ 安裝成功

# 3. 安裝 MLX 工具鏈（Apple Silicon 替代方案）
pip install mlx mlx-lm  # ✅ 安裝成功

# 4. 驗證
python3 -c "import torch; print('MPS:', torch.backends.mps.is_available())"
# 輸出: MPS: True
```

---

## 建議

1. **M3 Ultra 用戶強烈建議使用 `mlx_lm.lora`**，而非 Unsloth
2. Unsloth 適合 NVIDIA/AMD GPU 伺服器環境
3. `mlx_lm.lora` 提供類似的 API 設計，支援 LoRA/DoRA/full fine-tuning
4. 未來可關注 Unsloth 是否支援 Apple Silicon（GitHub Issue 已存在）

---

## 硬體利用率（M3 Ultra 96GB）

- **訓練記憶體佔用：** ~8.8 GB（Phi-4-mini-instruct QLoRA）
- **可訓練參數：** 5.767M / 3836M（0.15%）
- **GPU 利用率：** Metal GPU 加速
