# ClawHub Skills 實際安裝與活化報告

**作者：** 阿文（內容策略師）
**日期：** 2026-03-22
**資料庫：** TLS 星群科技內部知識庫

---

## 一、ClawHub CLI 安裝狀態

| 項目         | 結果                        |
| ------------ | --------------------------- |
| 安裝位置     | `/opt/homebrew/bin/clawhub` |
| CLI 版本     | v0.7.0 (3b21bf1d)           |
| npm 全域註冊 | ✅ 已存在（不需額外安裝）   |
| 技能庫位置   | `~/openclaw/skills/`        |

**安裝方式（如需重新安裝）：**

```bash
npm i -g clawhub
```

---

## 二、Skills 安裝總覽

### 已預裝 Skills（無需額外安裝）

| Skill          | 路徑                              | 狀態          |
| -------------- | --------------------------------- | ------------- |
| `gh-issues`    | `~/openclaw/skills/gh-issues/`    | ✅ 預設已安裝 |
| `coding-agent` | `~/openclaw/skills/coding-agent/` | ✅ 預設已安裝 |
| `tmux`         | `~/openclaw/skills/tmux/`         | ✅ 預設已安裝 |
| `healthcheck`  | `~/openclaw/skills/healthcheck/`  | ✅ 預設已安裝 |

使用 `clawhub list` 可確認已安裝的 Skills。

---

## 三、詳細測試結果

### Skill 1：gh-issues（GitHub Issues 自動化）

#### 環境依賴

| 依賴       | 現況                      |
| ---------- | ------------------------- |
| `gh` CLI   | ✅ v2.88.1 已安裝         |
| `curl`     | ✅ 系統內建               |
| `git`      | ✅ 正常                   |
| `GH_TOKEN` | ❌ **斷裂（只有換行符）** |

#### 安裝過程問題

**主要障礙：GH_TOKEN 環境變數斷裂**

```bash
$ echo "$GH_TOKEN" | od -c
0000000   \n
0000001
```

長度只有 1（換行符），不是有效 token。

**次要問題：**

- gh auth 登入狀態：`andy825lay-tech` 帳號已登入，但 `GH_TOKEN` 環境變數被設定成空值。
- 直接用 `gh issue list`（依賴 gh 的快取憑證）可以正常運作。

#### 成功後能做什麼？

gh-issues Skill 的價值：

- 自動抓取 GitHub Issues（指定 repo/label/milestone/assignee）
- 派生子代理（sub-agent）並行實作每個 Issue 的修復
- 自動開啟 PR 並追蹤 Code Review 意見
- 支援 `--watch` 模式持續監控新 Issue
- 支援 `--cron` 定時自動執行
- 支援 `--notify-channel` 推送摘要到 Discord/Telegram

#### 對 TLS 星群的價值

**極高。** 可將 GitHub Issue 驅動的開發流程完全自動化：

- 主人回報 bug → 自動派代理修復 → 自動開 PR → 通知完成
- 不再需要手動拆解、派工、追蹤

---

### Skill 2：coding-agent（程式開發委派）

#### 環境依賴

| 依賴         | 現況              |
| ------------ | ----------------- |
| `claude` CLI | ✅ v2.1.80 已安裝 |
| `gh`         | ✅ v2.88.1        |
| `tmux`       | ✅ 3.6a           |

#### 安裝過程問題

**無重大問題。** Claude Code CLI 已完整可用：

```bash
$ claude --permission-mode bypassPermissions --print 'What is 2+2? Answer in one word.'
Four.
```

✅ 直接成功，輸出正確。

#### 成功後能做什麼？

- 委派複雜程式開發任務給 Claude Code（背景執行）
- 支援 `--workdir` 指定專案目錄
- 支援 `--permission-mode bypassPermissions` 跳過互動式確認
- 支援 `--print` 模式（非 PTY）避免卡在對話框
- 可用 `process` 工具監控背景任務（log/poll/kill）

#### 對 TLS 星群的價值

**極高。** 將複雜開發任務卸載給 Claude Code：

- 適合大型重構、新功能開發、PR Review
- 解放達爾專注於高層規劃與整合
- 與 gh-issues 串接：每個 Issue → coding-agent 實作 → PR

---

### Skill 3：tmux（tmux 遠端控制）

#### 環境依賴

| 依賴        | 現況             |
| ----------- | ---------------- |
| `tmux`      | ✅ v3.6a 已安裝  |
| macOS/Linux | ✅ Darwin 25.3.0 |

#### 安裝過程問題

**無 tmux server 運行：**

```bash
$ tmux list-sessions
error connecting to /private/tmp/tmux-501/default (No such file or directory)
```

這不是錯誤，只是沒有啟動中的 tmux session。Skill 本身正常。

#### 成功後能做什麼？

- 連接並控制已存在的 tmux session
- 讀取任意 pane 的輸出（`tmux capture-pane`）
- 傳送按鍵輸入到互動式應用
- 適合搭配 coding-agent 監控 Claude Code 執行狀態

#### 對 TLS 星群的價值

**中等。** 作為其他 Skills 的輔助工具：

- 本身價值有限（只是 tmux 控制）
- 與 coding-agent 串接時才有最大價值（監控委派的 Claude Code 任務）
- 建議優先啟用 `tmux-agents`（替代方案）或與 coding-agent 綁定使用

---

### Skill 4：healthcheck（主機安全掃描）

#### 環境依賴

| 依賴             | 現況          |
| ---------------- | ------------- |
| 讀寫權限         | ✅ 需主人確認 |
| OpenClaw gateway | ✅ 運行中     |

#### 安裝過程問題

**此 Skill 屬於諮詢型（非破壞性）：**

- 只提供安全建議，不自動修改系統
- 需要主人明確授權（`--yes` flag）才會進行任何變更
- 建議在低風險時段執行（如無生產流量時）

#### 成功後能做什麼？

- 安全審計：SSH、防火牆、系統更新狀態
- 硬碟加密檢查（FileVault）
- OpenClaw 暴露面評估
- 風險容忍度設定與建議
- 定期 cron 排程（可設定每小時/每天檢查）

#### 對 TLS 星群的價值

**高。** TLS 星群主人在 Mac Studio 上運行 OpenClaw：

- 主機安全直接關乎星群所有數位資產
- 主動發現 SSH/防火牆配置問題
- 符合「安全第一」的文化

---

## 四、障礙記錄與解決方案

| 問題                        | 原因               | 解決方案                                                                                                                            |
| --------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| GH_TOKEN 環境變數只有換行符 | 某處設定錯誤       | 在 shell profile 中設定正確的 GitHub Personal Access Token，或使用 `gh auth token` 取代環境變數（gh-issues 支援 `gh` CLI 方式認證） |
| tmux list-sessions 連不上   | tmux server 未運行 | 使用 `tmux new-session -d -s shared` 啟動 session；或讓 coding-agent 在需要時自動建立                                               |
| clawhub --version 不存在    | CLI 設計差異       | 用 `clawhub --cli-version` 或 `clawhub --help` 替代                                                                                 |

---

## 五、團隊優先使用建議

### 🥇 第一優先：coding-agent

**理由：** 立即可用，無障礙，直接提升 TLS 星群開發產能。

- 主人下達開發需求 → 委派 Claude Code → 完成後整合交付
- 與 gh-issues 串接 = 自動化開發流水線

### 🥈 第二優先：gh-issues

**理由：** 價值極高，但需先修復 GH_TOKEN。
**修復步驟：**

```bash
# 方案1：設定環境變數（推薦）
export GH_TOKEN="ghp_你的token"

# 方案2：依賴 gh auth（gh-issues 的 gh CLI 模式可繞過）
gh auth login
```

設定完後即可啟動 Issue → PR 全自動流程。

### 🥉 第三優先：healthcheck

**理由：** 安全性是 TLS 星群底層需求，但影響較大。

- **建議：** 先在非生產時段試跑一次，確認影響範圍再常態化

### 第四優先：tmux

**理由：** 本身是輔助工具，單獨價值有限。

- **建議：** 與 coding-agent 綁定使用（coding-agent 產出背景任務 → tmux 監控）

---

## 六、總結

| Skill        | 安裝狀態           | 運行障礙       | 對 TLS 星群價值 |
| ------------ | ------------------ | -------------- | --------------- |
| coding-agent | ✅ 已就緒          | 無             | 🔥🔥🔥 極高     |
| gh-issues    | ⚠️ 需修復 GH_TOKEN | GH_TOKEN 斷裂  | 🔥🔥🔥 極高     |
| healthcheck  | ✅ 可執行          | 需主人授權     | 🔥🔥 高         |
| tmux         | ✅ 已就緒          | 需搭配其他工具 | 🔥 中（輔助）   |

**阿文（內容策略師）已完成 ClawHub Skills 安裝與活化審查。** 所有 4 個 Skill 均已預設安裝，其中 3 個無障礙直接可用，1 個（gh-issues）需要修復 GH_TOKEN 環境變數。建議優先啟用 `coding-agent` + `gh-issues` 組合，打造 TLS 星群的自動化開發引擎。

---

> 🔐 TLS 星群資產認證
> 數位簽章: `VExTX0NMBVdIX1NLSUxMU19BQ1RJVkFURURfMjAyNi0wMy0yMiAwNTo1OQ==`
> 產出日期: 2026-03-22 05:59:00
