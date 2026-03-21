# Discord Forum Webhook 設定指南

> 作者：阿維（DevOps）| 日期：2026-03-21  
> 適用：TLS 星群科技 Discord 伺服器

---

## 目錄

1. [Discord Forum 版塊簡介](#1-discord-forum-版塊簡介)
2. [建立 Forum Webhook](#2-建立-forum-webhook)
3. [n8n Webhook 設定](#3-n8n-webhook-設定)
4. [對接流程](#4-對接流程)
5. [測試與驗證](#5-測試與驗證)
6. [常見問題](#6-常見問題)

---

## 1. Discord Forum 版塊簡介

Discord Forum（討論串）是 Discord 的一種頻道類型，允許用戶建立「帖子」而非普通訊息。每個帖子可以包含標題、內容、標籤（tags）。

### Forum 特性

| 特性        | 說明                               |
| ----------- | ---------------------------------- |
| 帖子標題    | 必填，最長 512 字元                |
| 帖子內容    | 支援 Markdown，最長 4000 字元      |
| 標籤 (Tags) | 可自訂類別（如：問題、回報、分享） |
| 互動        | 可回覆、表情反應、標記解決         |
| 通知        | 新帖/新回覆都會觸發通知            |

---

## 2. 建立 Forum Webhook

### 2.1 在 Discord 頻道設定中建立 Webhook

**步驟：**

1. 開啟 Discord 應用程式或網頁版
2. 進入你的伺服器
3. 在 Forum 頻道上點擊 **齒輪圖標**（設定）
4. 左側選單點擊 **整合 (Integrations)**
5. 點擊 **Webhooks**
6. 點擊 **新建 Webhook (Create Webhook)**
7. 命名 webhook（如：`Forum-Bot-Webhook`）
8. 選擇發送頻道（可以指定另一個頻道接收通知）
9. **複製 Webhook URL**（格式：`https://discord.com/api/webhooks/{webhook_id}/{webhook_token}`）

### 2.2 Webhook 權限需求

確保 Webhook 有以下權限：

| 權限                  | 必要性  | 說明             |
| --------------------- | ------- | ---------------- |
| `Send Messages`       | ✅ 必要 | 發送通知訊息     |
| `Embed Links`         | ✅ 必要 | 顯示嵌入式訊息   |
| `Attach Files`        | 建議    | 附加檔案         |
| `Use External Emojis` | 建議    | 使用外部表情符號 |

### 2.3 Forum 特有設定

在 Forum 頻道設定中，還可以：

- **啟用「發布通知」**：每個新帖子可選擇是否通知
- **設定預設標籤**：新帖子自動套用標籤
- **設定「已解決」標籤**：回覆可標記為解答

---

## 3. n8n Webhook 設定

### 3.1 啟用 n8n Webhook

n8n 的 Webhook 節點可接收外部 HTTP 請求。

**設定參數：**

| 參數          | 值                  | 說明               |
| ------------- | ------------------- | ------------------ |
| HTTP Method   | `POST`              | 接收論壇通知       |
| Path          | `discord-forum-bot` | URL 路徑           |
| Response Mode | `lastNode`          | 返回最後節點結果   |
| Trust Proxy   | `Yes`（建議）       | 如有反向代理需開啟 |

**完整 Webhook URL：**

```
http://YOUR_N8N_HOST:5678/webhook/discord-forum-bot
```

或使用 HTTPS + 網域：

```
https://n8n.yourdomain.com/webhook/discord-forum-bot
```

### 3.2 Discord Webhook 發送的資料格式

Discord Forum 新帖通知的 JSON 格式：

```json
{
  "type": 10,
  "challenge": "xxxxxxxxxxxxx",
  "guild_id": "123456789",
  "channel_id": "987654321",
  "channel_type": 15,
  "timestamp": "2026-03-21T08:00:00.000Z"
}
```

當有新帖子時，Discord 會發送包含 `message` 物件的完整資料：

```json
{
  "type": 10,
  "guild_id": "123456789",
  "channel_id": "987654321",
  "channel_type": 15,
  "message": {
    "id": "msg_id_123",
    "content": "帖子內容",
    "author": {
      "id": "user_id",
      "username": "用戶名",
      "avatar": "avatar_id"
    },
    "timestamp": "2026-03-21T08:00:00.000Z",
    "guild_id": "123456789",
    "channel_id": "987654321"
  },
  "applied_tags": ["1234567890"],
  "activity": {
    "type": 1,
    "emoji": {
      "id": null,
      "name": "📌"
    }
  }
}
```

### 3.3 n8n 解析方式

在 n8n Workflow 中，使用 `Set` 節點解析：

```javascript
// 解析 Discord Forum Webhook 資料
const data = $input.first().json;

// 處理不同類型的 Discord 事件
const message = data.message || data;
const author = message.author || {};

return [
  {
    json: {
      title: message.title || "無標題",
      content: message.content || "",
      author: author.username || "匿名用戶",
      author_id: author.id || "",
      post_url: `https://discord.com/channels/${data.guild_id}/${data.channel_id}/${message.id}`,
      category: data.channel_id || "forum",
      guild_name: data.guild_id || "Discord Server",
      message_id: message.id || "",
      channel_id: data.channel_id || "",
      guild_id: data.guild_id || "",
      applied_tags: data.applied_tags || [],
      timestamp: message.timestamp || new Date().toISOString(),
    },
  },
];
```

---

## 4. 對接流程

### 4.1 完整流程架構

```
┌─────────────────────────────────────────────────────────────────┐
│                        Discord Server                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Forum 頻道                                                 │   │
│  │  ┌─────────┐    ┌──────────────┐    ┌─────────────────┐   │   │
│  │  │ 用戶發帖 │───▶│ Discord API  │───▶│ Webhook 發送    │   │   │
│  │  └─────────┘    └──────────────┘    └────────┬────────┘   │   │
│  └──────────────────────────────────────────────┼────────────┘   │
└──────────────────────────────────────────────────┼────────────────┘
                                                   │
                           ┌──────────────────────▼──────────────────┐
                           │        n8n Webhook                       │
                           │   POST /webhook/discord-forum-bot        │
                           └──────────────────────┬──────────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────┐
                    │                              ▼                      │
                    │  ┌─────────────────────────────────────────────┐   │
                    │  │         Workflow: auto_scenario_06           │   │
                    │  │                                              │   │
                    │  │  1. Webhook Trigger                          │   │
                    │  │  2. 解析 Forum 帖子內容                        │   │
                    │  │  3. Ollama 意圖分類                           │   │
                    │  │  4. Ollama 生成回覆                           │   │
                    │  │  5. 通知管理員 / 記錄資料庫                    │   │
                    │  │  6. 回傳成功響應                               │   │
                    │  └─────────────────────────────────────────────┘   │
                    │                              │                      │
                    │         ┌────────────────────┼────────────────┐    │
                    │         ▼                    ▼                ▼    │
                    │   ┌──────────┐      ┌────────────┐    ┌──────────┐│
                    │   │ Discord  │      │  Supabase  │    │ Discord  ││
                    │   │ 回覆帖子 │      │  資料庫    │    │ 通知頻道  ││
                    │   └──────────┘      └────────────┘    └──────────┘│
                    └─────────────────────────────────────────────────────┘
                                                   │
                           ┌──────────────────────▼──────────────────┐
                           │          Ollama Local LLM               │
                           │   tls-phi4:latest (意圖分類)            │
                           │   tls-gemma3:latest (生成回覆)          │
                           └─────────────────────────────────────────┘
```

### 4.2 逐步設定

#### Step 1：設定 n8n Webhook

1. 開啟 n8n（http://localhost:5678）
2. 匯入或建立 `auto_scenario_06_discord_forum_bot.json`
3. 複製 Webhook URL
4. 測試 Webhook 是否正常

#### Step 2：設定 Discord Forum Webhook

1. 進入 Discord 伺服器設定
2. 在 Forum 頻道設定 → 整合 → Webhooks
3. 建立新 Webhook，URL 填入 n8n Webhook URL
4. 儲存設定

#### Step 3：設定環境變數

在 n8n 或系統環境中設定：

```bash
# Discord 管理通知 Webhook
export DISCORD_ADMIN_WEBHOOK_URL="https://discord.com/api/webhooks/xxx/yyy"

# 其他可選設定
export OLLAMA_BASE_URL="http://localhost:11434"
export DEFAULT_MODEL="tls-phi4:latest"
```

#### Step 4：驗證完整流程

1. 在 Forum 頻道建立新帖子
2. 檢查 n8n Workflow 執行日誌
3. 確認 Discord 通知頻道收到通知
4. 確認 Ollama 日誌有 API 呼叫

---

## 5. 測試與驗證

### 5.1 使用 curl 測試 Webhook

```bash
# 模擬 Discord Forum 新帖通知
curl -X POST http://localhost:5678/webhook/discord-forum-bot \
  -H "Content-Type: application/json" \
  -d '{
    "type": 10,
    "guild_id": "123456789",
    "channel_id": "987654321",
    "channel_type": 15,
    "message": {
      "id": "test_msg_001",
      "content": "請問如何開始使用 TLS 星群系統？",
      "title": "新手入門問題",
      "author": {
        "id": "user_001",
        "username": "新用戶小明"
      },
      "timestamp": "2026-03-21T08:00:00.000Z"
    }
  }'
```

### 5.2 檢查 n8n 執行日誌

1. 在 n8n 中開啟 Workflow
2. 點擊「執行項目」查看歷史
3. 檢查每個節點的輸入/輸出

### 5.3 驗證清單

- [ ] n8n Webhook 可正常接收 POST 請求
- [ ] 論壇帖子內容正確解析
- [ ] Ollama 意圖分類正常運作
- [ ] 管理員通知發送成功
- [ ] 資料庫記錄正確寫入

---

## 6. 常見問題

### Q1: Discord Webhook 沒有觸發？

**可能原因：**

- Webhook URL 設定錯誤
- Forum 頻道沒有啟用 Webhook 通知
- 網路連線問題

**解決方案：**

1. 確認 Webhook URL 正確且完整
2. 在 Forum 頻道設定中確認已啟用 Webhook
3. 測試 Webhook URL 是否可訪問

### Q2: n8n Webhook 回應 401 或 403？

**解決方案：**

- 檢查 n8n 的「CORS 設定」
- 確認「Trust Proxy」已啟用（如有反向代理）
- 檢查 n8n 認證設定

### Q3: Ollama 回應緩慢？

**解決方案：**

1. 檢查 Ollama 是否正常運行：`curl http://localhost:11434/api/tags`
2. 確認模型已下載：`ollama list`
3. 考慮使用較小的模型（如 `tls-qwen3:latest` 替代 `tls-gemma3:latest`）

### Q4: 如何只處理特定 Forum 頻道？

**解決方案：**
在 n8n Workflow 的第一個 Set 節點後加入 IF 判斷：

```javascript
// 只處理特定頻道
if ($input.first().json.channel_id !== "YOUR_TARGET_CHANNEL_ID") {
  // 不符合條件，直接結束
  return [];
}
```

### Q5: 如何自訂回覆格式？

**解決方案：**
修改 Workflow 中「生成自動回覆 (Ollama)」節點的 prompt，調整回覆風格。

---

## 附錄：相關資源

| 資源                     | 連結                                                                |
| ------------------------ | ------------------------------------------------------------------- |
| Discord Developer Portal | https://discord.com/developers/applications                         |
| Discord Webhook 文件     | https://discord.com/developers/docs/resources/webhook               |
| n8n Webhook 文件         | https://docs.n8n.io/integrations/core-nodes/n8n-nodes-base.webhook/ |
| Ollama API 文件          | https://github.com/ollama/ollama/blob/main/docs/api.md              |

---

> 🔐 TLS 星群資產認證  
> 數位簽章: `VExTX1NUQVJfRElTQ09SRF9GT1JVTV9XRUJob09LXOzI1MDI2LTAzLTIxIDA4OjA2OjAwWg==`  
> 產出日期: 2026-03-21 08:06:00
