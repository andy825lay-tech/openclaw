#!/usr/bin/env python3
"""
RAG Batch Ingest Script - 批次文件攝入腳本
阿智（AI 工程師）+ 阿工（CTO）產出
v2.0 - 2026-03-21

功能：
- 支援資料夾批量攝入（遞迴掃描）
- 自動 chunking（512 tokens，overlap 128）
- Ollama embeddings（nomic-embed-text）
- 寫入 Qdrant collection
- 進度顯示 + 錯誤處理
"""

import os
import sys
import time
import hashlib
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import tiktoken
import threading

# ── Configuration ──────────────────────────────────────────────────────────────
QDRANT_HOST = "http://localhost:6333"
OLLAMA_HOST = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
DEFAULT_COLLECTION = "tls_knowledge"

CHUNK_TOKENS = 512
OVERLAP_TOKENS = 128
BATCH_SIZE = 10
EMBED_WORKERS = 4  # 嵌入並行數

# ── Tokenizer ─────────────────────────────────────────────────────────────────
def get_tokenizer():
    """取得 tiktoken 分詞器"""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None

# ── Text Chunking ─────────────────────────────────────────────────────────────
def chunk_text(text: str, tokenizer: Optional[tiktoken.Encoding] = None) -> List[Dict[str, Any]]:
    """
    將文字分塊：CHUNK_TOKENS 大小，OVERLAP_TOKENS 重疊
    Returns: List of {"text": str, "start": int, "end": int, "total_tokens": int}
    """
    if not text or not text.strip():
        return []

    if tokenizer is None:
        # Fallback: 按段落分塊
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < CHUNK_TOKENS * 4:
                current += "\n\n" + para
            else:
                if current:
                    chunks.append({
                        "text": current.strip(),
                        "start": 0,
                        "end": len(current),
                        "total_tokens": len(current.split())
                    })
                current = para
        if current:
            chunks.append({
                "text": current.strip(),
                "start": 0,
                "end": len(current),
                "total_tokens": len(current.split())
            })
        return chunks

    tokens = tokenizer.encode(text)
    total_tokens = len(tokens)

    if total_tokens <= CHUNK_TOKENS:
        return [{
            "text": text,
            "start": 0,
            "end": len(text),
            "total_tokens": total_tokens
        }]

    chunks = []
    start = 0

    while start < total_tokens:
        end = min(start + CHUNK_TOKENS, total_tokens)
        chunk_tokens = tokens[start:end]

        # 找到自然邊界（句號、換行）
        chunk_text = tokenizer.decode(chunk_tokens)
        if end < total_tokens:
            # 嘗試在句號或換行處截斷
            for sep in ['\n\n', '。', '.\n', '！', '？', '.\n']:
                last_sep = chunk_text.rfind(sep)
                if last_sep > len(chunk_text) * 0.5:
                    chunk_text = chunk_text[:last_sep + len(sep)]
                    break

        chunks.append({
            "text": chunk_text.strip(),
            "start": start,
            "end": end,
            "total_tokens": len(tokenizer.encode(chunk_text))
        })

        # 重疊滑動
        start = end - OVERLAP_TOKENS
        if start >= total_tokens - OVERLAP_TOKENS:
            break

    return [c for c in chunks if c["text"].strip()]

# ── Embeddings ────────────────────────────────────────────────────────────────
def embed_text(texts: List[str], verbose: bool = True) -> List[Optional[List[float]]]:
    """使用 Ollama 嵌入模型產生向量（批次）"""
    results = []
    semaphore = threading.Semaphore(EMBED_WORKERS)

    def _embed_one(text: str) -> Optional[List[float]]:
        with semaphore:
            try:
                truncated = text[:8192]  # Ollama 有長度限制
                with httpx.Client(timeout=60) as client:
                    r = client.post(
                        f"{OLLAMA_HOST}/api/embeddings",
                        json={"model": EMBED_MODEL, "prompt": truncated}
                    )
                    r.raise_for_status()
                    return r.json().get("embedding")
            except Exception as e:
                if verbose:
                    print(f"    [嵌入錯誤] {e}")
                return None

    with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as executor:
        futures = {executor.submit(_embed_one, t): t for t in texts}
        for future in as_completed(futures):
            results.append(future.result())

    return results

# ── Qdrant ────────────────────────────────────────────────────────────────────
def ensure_collection_exists(collection: str, vector_size: int = 768) -> bool:
    """確保 collection 存在"""
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{QDRANT_HOST}/collections/{collection}")
            if r.status_code == 200:
                return True

        # 創建 collection
        with httpx.Client(timeout=30) as client:
            r = client.put(
                f"{QDRANT_HOST}/collections/{collection}",
                json={
                    "vectors": {
                        "size": vector_size,
                        "distance": "Cosine"
                    }
                }
            )
            return r.status_code in (200, 201)
    except Exception as e:
        print(f"  [Qdrant 錯誤] {e}")
        return False

def upsert_points(collection: str, points: List[Dict]) -> bool:
    """寫入 points 到 Qdrant"""
    try:
        with httpx.Client(timeout=30) as client:
            r = client.put(
                f"{QDRANT_HOST}/collections/{collection}/points",
                json={"points": points}
            )
            return r.status_code in (200, 201)
    except Exception as e:
        print(f"  [Qdrant 寫入錯誤] {e}")
        return False

def generate_point_id(source: str, chunk_idx: int, text: str) -> int:
    """產生穩定的 point ID（Qdrant 要求整數或 UUID）"""
    key = f"{source}:{chunk_idx}:{text[:50]}"
    # 使用前8位 hex → 轉為 int，確保唯一且穩定
    hex_str = hashlib.sha256(key.encode()).hexdigest()[:16]
    return int(hex_str, 16) % (2**63 - 1)

# ── Document Processing ───────────────────────────────────────────────────────
def read_document(path: Path) -> Optional[str]:
    """讀取文檔（支援 UTF-8 / Latin-1）"""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    print(f"  [錯誤] 無法解讀: {path}")
    return None

def scan_files(
    root: Path,
    extensions: tuple = (".md", ".txt", ".json"),
    exclude_dirs: tuple = ("node_modules", ".git", "__pycache__", ".venv")
) -> List[Path]:
    """遞迴掃描目錄下的文件"""
    files = []
    for ext in extensions:
        for f in root.rglob(f"*{ext}"):
            # 排除特定目錄
            if any(ex in f.parts for ex in exclude_dirs):
                continue
            files.append(f)
    return sorted(files)

# ── Single File Processing ─────────────────────────────────────────────────────
def process_file(
    file_path: Path,
    source_root: Path,
    collection: str,
    tokenizer,
    show_progress: bool = True
) -> Dict[str, Any]:
    """處理單一文件：讀取 → 分塊 → 嵌入 → 上傳"""
    rel_path = str(file_path.relative_to(source_root))

    if show_progress:
        print(f"  📄 {rel_path}")

    content = read_document(file_path)
    if content is None:
        return {"file": rel_path, "status": "read_failed", "chunks": 0}

    # JSON 特殊處理
    if file_path.suffix == ".json":
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                content = json.dumps(data, ensure_ascii=False, indent=2)
            elif isinstance(data, list):
                content = "\n".join(json.dumps(item, ensure_ascii=False) for item in data)
        except Exception:
            pass

    chunks = chunk_text(content, tokenizer)
    if not chunks:
        return {"file": rel_path, "status": "no_content", "chunks": 0}

    texts = [c["text"] for c in chunks]

    # 嵌入
    embeddings = embed_text(texts, verbose=False)

    # 建 points
    points = []
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        if emb is None:
            continue
        points.append({
            "id": generate_point_id(str(file_path), idx, chunk["text"]),
            "vector": emb,
            "payload": {
                "source": rel_path,
                "full_path": str(file_path),
                "chunk_index": idx,
                "text": chunk["text"][:2000],
                "start_token": chunk["start"],
                "end_token": chunk["end"],
                "total_tokens": chunk.get("total_tokens", 0),
                "file_ext": file_path.suffix,
                "ingested_at": datetime.now().isoformat()
            }
        })

    # 上傳
    uploaded = 0
    if points:
        total_batches = (len(points) + BATCH_SIZE - 1) // BATCH_SIZE
        for i in range(total_batches):
            batch = points[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
            if upsert_points(collection, batch):
                uploaded += len(batch)

    if show_progress:
        print(f"    → {len(chunks)} chunks, 上傳 {uploaded}")

    return {
        "file": rel_path,
        "status": "success" if uploaded > 0 else "upload_failed",
        "chunks": len(chunks),
        "uploaded": uploaded,
        "failed": len(points) - uploaded
    }

# ── Batch Ingestion ────────────────────────────────────────────────────────────
def batch_ingest(
    source_dirs: List[Path],
    collection: str = DEFAULT_COLLECTION,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    批次攝入多個目錄

    Returns:
        {"success": bool, "total_files": int, "total_chunks": int,
         "uploaded": int, "failed": int, "details": []}
    """
    tokenizer = get_tokenizer()

    # 確保 collection 存在
    if not ensure_collection_exists(collection):
        print(f"❌ Collection '{collection}' 不存在或無法創建")
        return {"success": False}

    # 收集所有文件
    all_files = []
    for root in source_dirs:
        if not root.exists():
            print(f"⚠️  目錄不存在: {root}")
            continue
        files = scan_files(root)
        all_files.extend(files)
        if verbose:
            print(f"  📂 {root}: 找到 {len(files)} 個文件")

    if not all_files:
        print("❌ 找不到任何文件")
        return {"success": False}

    if verbose:
        print(f"\n🚀 開始攝入 {len(all_files)} 個文件...\n")

    stats = {
        "success": True,
        "total_files": len(all_files),
        "total_chunks": 0,
        "uploaded": 0,
        "failed": 0,
        "details": []
    }

    for i, file_path in enumerate(all_files, 1):
        if verbose:
            print(f"[{i}/{len(all_files)}]", end=" ")

        result = process_file(
            file_path=file_path,
            source_root=file_path.parent if file_path.parent in source_dirs else source_dirs[0],
            collection=collection,
            tokenizer=tokenizer,
            show_progress=verbose
        )

        stats["total_chunks"] += result.get("chunks", 0)
        stats["uploaded"] += result.get("uploaded", 0)
        stats["failed"] += result.get("failed", 0)
        stats["details"].append(result)

        if result["status"] != "success":
            stats["success"] = False

    return stats

# ── CLI Entry Point ───────────────────────────────────────────────────────────
def main():
    import argparse
    import subprocess

    # Capture defaults before argparse affects local scope
    default_chunk = CHUNK_TOKENS
    default_overlap = OVERLAP_TOKENS

    parser = argparse.ArgumentParser(
        description="RAG Batch Ingest - 批次文件攝入",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python rag_batch_ingest.py                                    # 攝入 knowledge/
  python rag_batch_ingest.py -s ./knowledge -c tls_knowledge   # 指定目錄
  python rag_batch_ingest.py -s ./knowledge -s ./docs -c tls_full_archive  # 多目錄
  python rag_batch_ingest.py --dry-run                          # 僅預覽
        """
    )
    parser.add_argument(
        "-s", "--source", dest="sources", action="append",
        type=Path,
        help="來源目錄（可多次指定）"
    )
    parser.add_argument(
        "-c", "--collection", default=DEFAULT_COLLECTION,
        help=f"Qdrant collection 名稱（預設: {DEFAULT_COLLECTION}）"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="僅預覽要攝入的文件，不實際上傳"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="安靜模式"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=default_chunk,
        help=f"每個 chunk 的 token 數（預設: {default_chunk}）"
    )
    parser.add_argument(
        "--overlap", type=int, default=default_overlap,
        help=f"相鄰 chunk 重疊 token 數（預設: {default_overlap}）"
    )
    parser.add_argument(
        "--ext", dest="extensions", action="append",
        default=[".md", ".txt", ".json"],
        help="要掃描的副檔名（預設: .md .txt .json）"
    )

    args = parser.parse_args()

    # 預設來源
    if not args.sources:
        workspace = Path(__file__).parent.parent
        args.sources = [workspace / "knowledge"]
        # 加入其他常見目錄
        for d in ["docs", "data", "memory"]:
            p = workspace / d
            if p.exists():
                args.sources.append(p)

    if not args.quiet:
        print("=" * 60)
        print("RAG Batch Ingest v2.0")
        print("=" * 60)
        print(f"Qdrant:      {QDRANT_HOST}")
        print(f"Ollama:      {OLLAMA_HOST}")
        print(f"Embed Model: {EMBED_MODEL}")
        print(f"Collection:  {args.collection}")
        print(f"Chunk Size:  {CHUNK_TOKENS} tokens, overlap {OVERLAP_TOKENS}")
        print(f"Sources:     {', '.join(str(s) for s in args.sources)}")
        print("-" * 60)

    # Dry run
    if args.dry_run:
        for root in args.sources:
            files = scan_files(root, tuple(args.ext))
            print(f"  📂 {root}: {len(files)} 個文件")
            for f in files[:10]:
                print(f"    - {f.relative_to(root)}")
            if len(files) > 10:
                print(f"    ... 還有 {len(files) - 10} 個")
        return

    # 驗證 Ollama
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{OLLAMA_HOST}/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            if EMBED_MODEL not in models:
                print(f"⚠️  {EMBED_MODEL} 未載入，正在嘗試安裝...")
                subprocess.run([sys.executable, "-m", "ollama", "pull", EMBED_MODEL])
    except Exception as e:
        print(f"⚠️  Ollama 連線失敗: {e}")

    # 執行攝入
    stats = batch_ingest(
        source_dirs=args.sources,
        collection=args.collection,
        verbose=not args.quiet
    )

    # 輸出結果
    if not args.quiet:
        print()
        print("=" * 60)
        print("📊 攝入結果")
        print("=" * 60)
        print(f"  總文件數: {stats['total_files']}")
        print(f"  總分塊數: {stats['total_chunks']}")
        print(f"  上傳成功: {stats['uploaded']}")
        print(f"  失敗:     {stats['failed']}")
        print()

        if stats["uploaded"] > 0:
            print("✅ 攝入完成")
            # 寫入結果檔案
            result_file = Path(__file__).parent.parent / "knowledge" / "rag_batch_ingest_results.md"
            write_results_md(stats, str(result_file))
            print(f"   結果已寫入: {result_file}")
        else:
            print("⚠️  無資料上傳，請檢查錯誤")

if __name__ == "__main__":
    import subprocess
    main()

def write_results_md(stats: Dict[str, Any], output_path: str):
    """寫入攝入結果報告"""
    lines = [
        "# RAG Batch Ingest 結果報告",
        "",
        f"**日期：** {datetime.now().strftime('%Y-%m-%d %H:%M')} GMT+8",
        f"**執行者：** 阿智（AI 工程師）+ 阿工（CTO）",
        "",
        "## 📊 攝入摘要",
        "",
        "| 項目 | 數值 |",
        "|------|------|",
        f"| 總文件數 | {stats['total_files']} |",
        f"| 總分塊數 | {stats['total_chunks']} |",
        f"| 上傳成功 | {stats['uploaded']} |",
        f"| 失敗 | {stats['failed']} |",
        "",
        "## 📁 檔案明細",
        "",
        "| 檔案 | 狀態 | Chunks | 上傳 |",
        "|------|------|--------|------|",
    ]
    for d in stats.get("details", []):
        status_icon = "✅" if d["status"] == "success" else "❌"
        lines.append(f"| {d['file']} | {status_icon} {d['status']} | {d.get('chunks', 0)} | {d.get('uploaded', 0)} |")

    lines.append("")
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
