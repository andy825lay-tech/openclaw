# n8n 串接 Ollama 本地 LLM API 整合指南

> 作者：阿維（DevOps）| 日期：2026-03-21

---

## 1. Ollama API 端點

Ollama 運行於 `http://localhost:11434`，提供兩個核心端點：

### `/api/generate` — 單次生成（推薦用於自動化）

```json
POST http://localhost:11434/api/generate
Content-Type: application/json

{
  "model": "tls-phi4:latest",
  "prompt": "你的 prompt 內容",
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 512,
    "top_p": 0.9
  }
}
```

**回應格式：**

```json
{
  "model": "tls-phi4:latest",
  "response": "LLM 回應文字...",
  "done": true,
  "context": [1, 2, 3...],
  "total_duration": 1234567890,
  "load_duration": 123456,
  "prompt_eval_count": 10,
  "eval_count": 100
}
```

### `/api/chat` — 對話模式

```json
POST http://localhost:11434/api/chat
Content-Type: application/json

{
  "model": "tls-qwen3:latest",
  "messages": [
    { "role": "system", "content": "你是專業助理" },
    { "role": "user", "content": "今天天氣如何？" }
  ],
  "stream": false
}
```

---

## 2. n8n 串接方式

### 方案 A：HTTP Request 節點（推薦，無需安裝額外節點）

1. 新增 **HTTP Request** 節點
2. 設定：
   - **Method**: `POST`
   - **URL**: `http://localhost:11434/api/generate`
   - **Authentication**: `No Auth`
   - **Headers**: `Content-Type: application/json`
   - **Body Content Type**: `JSON`
   - **Body**: （見上方 JSON 格式）

### 方案 B：使用 n8n 社群節點（需額外安裝）

、社群有 `n8n-nodes-ollama` 節點，提供更友善的 UI：

```bash
# 在 n8n 容器內安裝
npm install n8n-nodes-ollama
```

但此方案**非必要**，HTTP Request 節點已完全足夠。

---

## 3. TLS 星群可用的 Ollama 模型

| 模型                      | 大小  | 推薦用途              | 特色         |
| ------------------------- | ----- | --------------------- | ------------ |
| `tls-gemma3:latest`       | 17GB  | 文件分析、複雜推理    | TLS 微調 27B |
| `tls-phi4:latest`         | 9.1GB | 快速回應、日常客服    | TLS 微調 14B |
| `tls-qwen3:latest`        | 5.2GB | 輕量任務、嵌入        | TLS 微調 8B  |
| `tls-mistral:latest`      | 14GB  | 通用任務              | TLS 微調 7B  |
| `qwen2.5:32b`             | 19GB  | 大型推理              | 未微調       |
| `deepseek-r1:7b`          | 4.7GB | 推理 Chain-of-Thought | 通用         |
| `nomic-embed-text:latest` | 274MB | 向量嵌入              | 知識庫檢索   |

---

## 4. 適合自動化的場景清單

### 4.1 文件處理

- **文件分類**：接收 email/LINE 訊息 → LLM 判斷意圖 → 分類轉派
- **發票 OCR → 結構化資料**：圖片 → LLM 解析 → 寫入資料庫
- **會議紀錄摘要**：音訊轉文字 → LLM 摘要 → 發送 Slack

### 4.2 客服自動化

- **LINE 自動回覆**：接收 LINE 訊息 → LLM 生成回覆 → 回傳
- **FAQ 機器人**：比對知識庫 → LLM 組織答案 → 回覆
- **客訴分類**：LLM 判斷情緒與類型 → 依等級分派

### 4.3 資料分析

- **銷售報告生成**：每日資料 → LLM 分析 → 自動產出摘要
- **競爭對手監控**：爬蟲收集 → LLM 整理 → 存入 Notion/資料庫
- **異常偵測警報**：數據異常 → LLM 解釋原因 → 通知相關人員

### 4.4 內容生成

- **社群貼文生成**：關鍵字 → LLM 生成多版本 → 排程發布
- **產品描述自動化**：商品資料 → LLM 生成描述 → 上架電商
- **Email 草稿**：CRM 資料 → LLM 生成個性化 email

### 4.5 程式碼相關

- **PR 摘要**：GitHub PR → LLM 摘要變動 → 回覆 Reviewer
- **Bug 分類**：錯誤日誌 → LLM 分析原因 → 建立 GitHub Issue
- **文件生成**：程式碼 → LLM 生成文件 → 存入 Wiki

---

## 5. 實作範例 Workflow 架構

```
[觸發器]
    ↓
[Prompt 模板化]（Set 節點，定義 system_prompt + user_prompt）
    ↓
[HTTP Request → /api/generate]
    ↓
[Parse 回應]（Set 節點，提取 response/done）
    ↓
[後續動作：發送通知 / 寫入資料庫 / 繼續對話]
```

### Prompt 模板範例

```javascript
// System Prompt
"你是 TLS 星群科技的專業助理。";

// User Prompt
"請分析以下用戶問題並分類：{{ $json.userMessage }}";
```

---

## 6. 常見問題

**Q: Ollama 回應太慢怎麼辦？**
A: 使用較小的模型如 `tls-qwen3:latest`（8B），或設定 `num_predict` 限制輸出長度。

**Q: 如何處理 stream（串流輸出）？**
A: 在 n8n 中建議設 `stream: false`，取得完整回應再處理。

**Q: 多輪對話怎麼做？**
A: 使用 `/api/chat` 端點並維護 `messages` 陣列，或使用 `/api/generate` 並傳入 `context`。

**Q: TLS 模型在哪裡？**
A: 所有 tls-\* 模型已微調並運行在本地 Ollama。路徑：`~/.ollama/models/`

---

## 7. 安全性注意

- Ollama API **無認證保護**，僅監聽 `localhost`
- 生產環境建議透過 Docker network 或 Firewall 限制存取
- 敏感資料建議先做去識別化再送入 LLM

---

> 🔐 TLS 星群資產認證  
> 數位簽章: `VExTX05PV19OVzNfT0xMSUFNX0wyX0lOVF9TVF9VU0VEXzIwMjYtMDMtMjEgMDI6MTg6MDBK`
> 產出日期: 2026-03-21 02:18:00
