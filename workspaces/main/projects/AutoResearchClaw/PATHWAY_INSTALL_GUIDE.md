# Pathway 安裝指南 v1.0

> 學習部 P1 任務產出 | 達爾統帥 | 2026-03-21

---

## 什麼是 Pathway？

Pathway 是一個 **Python ETL 框架**，專為以下場景設計：

- 即時資料流處理（Stream Processing）
- 動態 RAG（Retrieval-Augmented Generation）管線
- 即時數據分析
- LLM 應用開發

**核心特色：**

- Python-first API，但底層由 Rust 引擎驅動（Differential Dataflow）
- 支援增量計算（Incremental Computation）
- 統一 Batch + Streaming 處理
- 支援多執行緒、多程序、分散式運算
- 內建 LLM xpack：OpenAI、HuggingFace、Bedrock、Ollama 等整合

---

## 最新版本資訊

| 項目            | 資訊                                |
| --------------- | ----------------------------------- |
| **當前版本**    | `0.27.x`（2026-02-16 release）      |
| **Python 需求** | Python 3.10+                        |
| **作業系統**    | macOS（Intel/Apple Silicon）、Linux |
| **安裝方式**    | `pip install -U pathway`            |

> ⚠️ **Windows 用戶**：需使用 VM 或 Docker 執行

---

## Step-by-Step 安裝流程

### Step 1：確認環境

```bash
# 檢查 Python 版本
python3 --version
# 需 >= 3.10

# 確認 pip 可用
python3 -m pip --version
```

### Step 2：基本安裝（僅核心框架）

```bash
pip install -U pathway
```

### Step 3：安裝 LLM xpack（推薦）

Pathway 的 LLM 功能需要額外依賴：

```bash
# 僅 LLM 功能
pip install "pathway[xpack-llm]"

# 或完整安裝（所有 xpack）
pip install "pathway[all]"
```

額外相依套件（LLM 用）：

```bash
pip install pathway[xpack-llm] python-dotenv
```

### Step 4：驗證安裝

```bash
python3 -c "import pathway as pw; print(pw.__version__)"
```

---

## Hello World 測試流程

### 測試 1：基本 ETL（CSV 過濾與聚合）

```python
# hello_etl.py
import pathway as pw

# 定義資料 Schema
class InputSchema(pw.Schema):
    value: int

# 讀取 CSV 檔案
input_table = pw.io.csv.read(
    "./input/",
    schema=InputSchema
)

# 過濾與聚合
filtered_table = input_table.filter(input_table.value >= 0)
result_table = filtered_table.reduce(
    sum_value=pw.reducers.sum(filtered_table.value)
)

# 輸出到 JSONL
pw.io.jsonlines.write(result_table, "output.jsonl")

# 執行
pw.run()
```

**測試資料（input/data.csv）：**

```csv
value
10
-5
20
15
```

**執行：**

```bash
mkdir -p input
echo "value" > input/data.csv
echo "10" >> input/data.csv
echo "-5" >> input/data.csv
echo "20" >> input/data.csv
echo "15" >> input/data.csv
python3 hello_etl.py
cat output.jsonl
```

**預期輸出：** `{"sum_value": 45}`

---

### 測試 2：即時 LLM 管道（RAG 範例）

> 前提：需有 OpenAI API Key

```bash
# 設定 API Key
echo 'OPENAI_API_KEY="sk-your-key-here"' > .env
```

```python
# hello_rag.py
import pathway as pw
from pathway.xpacks.llm import llms
from pathway.xpacks.llm.embedders import OpenAIEmbedder
from pathway.xpacks.llm.document_store import DocumentStore

# 1. 讀取文件（範例：./data/ 目錄）
documents = pw.io.fs.read("./data/", format="binary", with_metadata=True)

# 2. 使用 OpenAI Embedder 建立向量索引
embedder = OpenAIEmbedder()

# 3. 建立 Document Store
store = DocumentStore(
    documents=documents,
    embedder=embedder,
)

# 4. 簡單 Query 處理
# 實際應用會結合 pw.io.http.rest_connector 做成 API
pw.run()
```

**完整 RAG 範例** 參考：

- [Pathway 官網 RAG 教程](https://pathway.com/developers/user-guide/llm-xpack/llm-app-pathway/)
- [GitHub: llm-app](https://github.com/pathwaycom/llm-app)
- [Colab 快速上手](https://colab.research.google.com/drive/1aBIJ2HCng-YEUOMrr0qtj0NeZMEyRz55)

---

### 測試 3：即時資料流（pw.run 與監控）

```python
# hello_stream.py
import pathway as pw

# 建立即時 API 輸入端點
input_table = pw.io.http.rest_connector(
    schema=pw.Schema意思,
    port=8000
)

# 簡單轉換
result = input_table.select(
    text=pw.this.text.upper()
)

# 輸出到控制台
pw.io.print(result)

pw.run()
```

```bash
python3 hello_stream.py
# 另開終端：
curl -X POST http://localhost:8000 -d '{"text":"hello"}'
```

---

## 已知相容性問題

### ⚠️ 高優先級

| 問題                                   | 說明                                                             | 解法                                                                    |
| -------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **Python 3.14 尚未官方測試**           | Pathway 官方文件說支援 3.10+，但 3.14 為最新版本，可能有邊緣問題 | 建議使用 3.11、3.12 或 3.13 進行正式專案                                |
| **paddlepaddle 移除依賴**              | v0.26+ 起不再內建 PaddlePaddle，需手動安裝                       | 參考 [PaddlePaddle 官網](https://www.paddlepaddle.org.cn/install/quick) |
| **macOS 僅支援 Apple Silicon + Intel** | 不支援 Windows                                                   | Windows 用戶使用 Docker/VM                                              |

### ⚠️ 中優先級

| 問題                    | 說明                                                     | 解法                                                                     |
| ----------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------ |
| **依賴眾多 LLM 套件**   | 安裝 `pathway[xpack-llm]` 會同時安裝 openai、tiktoken 等 | 確認磁碟空間充足                                                         |
| **Rust 引擎記憶體需求** | 大量資料時記憶體用量高                                   | 留意機器 RAM                                                             |
| **Breaking Changes**    | 近期版本有 Breaking Change（如 Iceberg API 改變）        | 升級前查 [Release Notes](https://github.com/pathwaycom/pathway/releases) |

### ℹ️ 低優先級（文件記錄）

| 問題                           | 說明                                                          |
| ------------------------------ | ------------------------------------------------------------- |
| Discord 社群活躍               | 有問題可至 [Pathway Discord](https://discord.gg/pathway) 詢問 |
| 企業版提供 Exactly-Once 一致性 | 開源版為 At-Least-Once                                        |

---

## 常見錯誤與排除

### 錯誤 1：`ModuleNotFoundError: No module named 'pathway'`

```bash
# 確認已安裝
pip show pathway
# 若無，安裝
pip install pathway
```

### 錯誤 2：`Python version not supported`

```bash
# 確認版本
python3 --version
# 若低於 3.10，升級 Python 或使用 conda/pyenv
```

### 錯誤 3：`OpenAI API Error`

```bash
# 確認 .env 檔案存在且格式正確
cat .env
# 必須是 OPENAI_API_KEY="sk-..."
```

---

## 官方資源

| 資源          | 連結                                     |
| ------------- | ---------------------------------------- |
| 官網          | https://pathway.com/                     |
| 官方文檔      | https://pathway.com/docs                 |
| GitHub        | https://github.com/pathwaycom/pathway    |
| Discord 社群  | https://discord.gg/pathway               |
| App Templates | https://pathway.com/developers/templates |
| PyPI          | https://pypi.org/project/pathway/        |

---

## 下一步建議

1. ✅ 先跑通基本 ETL 範例（測試 1）
2. ✅ 嘗試 Colab 上的 [Live Data Jupyter Notebook](https://colab.research.google.com/github/pathwaycom/pathway/blob/main/examples/notebooks/showcases/live-data-jupyter.ipynb)
3. ✅ 嘗試 [LLM RAG 範例](https://github.com/pathwaycom/llm-app)
4. 🔲 評估與現有 n8n/Supabase 架構整合可行性

---

> **🔐 TLS 星群資產認證**
> 產出代號: `LEARNING_P1_PATHWAY_20260321`
> 負責人: 達爾（學習部統帥）
