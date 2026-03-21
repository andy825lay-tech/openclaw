#!/usr/bin/env python3
"""
RAG Pipeline - Document Ingestion Script
阿智（AI 工程師）產出

功能：
- 讀取 markdown/txt 文件
- Chunking：512 tokens，overlap 128
- 使用 nomic-embed-text 嵌入（768維, cosine）
- 寫入 Qdrant collection（localhost:6333）
"""

import os
import sys
import time
import hashlib
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx
import tiktoken

# ── Configuration ──────────────────────────────────────────────────────────────
QDRANT_HOST = "http://localhost:6333"
OLLAMA_HOST = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "tls_knowledge"

CHUNK_TOKENS = 512
OVERLAP_TOKENS = 128
BATCH_SIZE = 10  # Qdrant upload batch size

# ── Tokenizer ─────────────────────────────────────────────────────────────────
def get_tokenizer() -> tiktoken.Encoding:
    """取得 tiktoken 分詞器（cl100k_base = GPT-4 相容）"""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback: 使用簡單的空格分詞
        return None

# ── Text Chunking ─────────────────────────────────────────────────────────────
def chunk_text(text: str, tokenizer: Optional[tiktoken.Encoding] = None) -> List[Dict[str, Any]]:
    """
    將文字分塊：CHUNK_TOKENS 大小，OVERLAP_TOKENS 重疊
    
    Returns:
        List of {"text": str, "start": int, "end": int}
    """
    if not text or not text.strip():
        return []
    
    if tokenizer is None:
        # Fallback: 按句子分塊（粗略）
        sentences = text.split('. ')
        chunks = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) < CHUNK_TOKENS * 4:  # 粗估
                current += sent + ". "
            else:
                if current.strip():
                    chunks.append({"text": current.strip(), "start": 0, "end": len(current)})
                current = sent + ". "
        if current.strip():
            chunks.append({"text": current.strip(), "start": 0, "end": len(current)})
        return chunks
    
    tokens = tokenizer.encode(text)
    total = len(tokens)
    
    if total <= CHUNK_TOKENS:
        return [{"text": tokenizer.decode(tokens), "start": 0, "end": total}]
    
    chunks = []
    step = CHUNK_TOKENS - OVERLAP_TOKENS  # 滑動窗口步進
    
    for i in range(0, total, step):
        chunk_tokens = tokens[i:i + CHUNK_TOKENS]
        chunk_text = tokenizer.decode(chunk_tokens)
        
        # 記錄 token 範圍（用於 metadata）
        chunk_info = {
            "text": chunk_text,
            "start": i,
            "end": i + len(chunk_tokens),
            "total_tokens": len(chunk_tokens)
        }
        chunks.append(chunk_info)
        
        if i + CHUNK_TOKENS >= total:
            break
    
    return chunks

# ── Ollama Embedding ─────────────────────────────────────────────────────────
def get_ollama_embedding(text: str, timeout: int = 60) -> Optional[List[float]]:
    """
    呼叫 Ollama API 取得文字嵌入向量
    
    Args:
        text: 要嵌入的文字
        timeout: 逾時秒數
    
    Returns:
        768維浮點向量，或 None（失敗時）
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("embedding")
    except httpx.HTTPStatusError as e:
        print(f"  [HTTP Error] {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"  [Error] Ollama embedding failed: {e}")
        return None

def batch_embeddings(texts: List[str], verbose: bool = True) -> List[Optional[List[float]]]:
    """
    批量取得嵌入向量
    
    Returns:
        List of embeddings (None for failed items)
    """
    results = []
    total = len(texts)
    
    for idx, text in enumerate(texts):
        if verbose:
            print(f"  Embedding [{idx+1}/{total}]...", end="", flush=True)
        
        emb = get_ollama_embedding(text)
        results.append(emb)
        
        if verbose:
            if emb:
                print(f" ✓ ({len(emb)} dims)")
            else:
                print(" ✗ FAILED")
        
        # 避免過快
        if idx < total - 1:
            time.sleep(0.1)
    
    return results

# ── Qdrant Operations ─────────────────────────────────────────────────────────
def qdrant_upsert_points(
    collection: str,
    points: List[Dict[str, Any]],
    wait: bool = True
) -> bool:
    """
    上傳 points 到 Qdrant collection
    
    Args:
        collection: collection 名稱
        points: list of {"id": str, "vector": List[float], "payload": dict}
        wait: 是否等待 indexing 完成
    
    Returns:
        True = 成功
    """
    try:
        url = f"{QDRANT_HOST}/collections/{collection}/points"
        params = {"wait": "true"} if wait else {}
        
        with httpx.Client(timeout=120) as client:
            # Qdrant expects {"points": [...]} format
            response = client.put(url, json={"points": points}, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "ok":
                return True
            else:
                print(f"  [Qdrant] Upsert returned: {result}")
                return False
    except Exception as e:
        print(f"  [Error] Qdrant upsert failed: {e}")
        return False

def generate_point_id(doc_path: str, chunk_index: int, chunk_text: str) -> str:
    """產生稳定的 UUID point ID"""
    unique = f"{doc_path}:{chunk_index}:{chunk_text[:50]}"
    hash_id = hashlib.sha256(unique.encode()).hexdigest()[:32]
    # Qdrant requires UUID format: insert 4 hyphens
    return f"{hash_id[0:8]}-{hash_id[8:12]}-{hash_id[12:16]}-{hash_id[16:20]}-{hash_id[20:32]}"

# ── File Reading ───────────────────────────────────────────────────────────────
def read_document(path: Path) -> Optional[str]:
    """讀取 markdown/txt 文件"""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="latin-1")
        except Exception as e:
            print(f"  [Error] Cannot read {path}: {e}")
            return None

def scan_documents(directory: Path, extensions: tuple = (".md", ".txt")) -> List[Path]:
    """掃描目錄下的文件"""
    files = []
    for ext in extensions:
        files.extend(directory.rglob(f"*{ext}"))
    return sorted(files)

# ── Main Ingestion Pipeline ───────────────────────────────────────────────────
def ingest_documents(
    source_dir: Path,
    collection: str = COLLECTION_NAME,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    主要攝入流程
    
    Returns:
        {"success": bool, "total_chunks": int, "uploaded": int, "failed": int, "details": []}
    """
    tokenizer = get_tokenizer()
    
    if verbose:
        print(f"\n📂 掃描文件: {source_dir}")
    
    files = scan_documents(source_dir)
    if not files:
        print(f"  ⚠️ 找不到 .md/.txt 文件")
        return {"success": False, "error": "No files found", "total_chunks": 0, "uploaded": 0, "failed": 0}
    
    if verbose:
        print(f"  找到 {len(files)} 個文件\n")
    
    stats = {
        "success": True,
        "total_chunks": 0,
        "uploaded": 0,
        "failed": 0,
        "details": []
    }
    
    for file_path in files:
        if verbose:
            print(f"📄 處理: {file_path.relative_to(source_dir)}")
        
        content = read_document(file_path)
        if content is None:
            stats["failed"] += 1
            stats["details"].append({"file": str(file_path), "status": "read_failed"})
            continue
        
        # 分塊
        chunks = chunk_text(content, tokenizer)
        if not chunks:
            stats["details"].append({"file": str(file_path), "status": "no_chunks"})
            continue
        
        if verbose:
            print(f"  分塊: {len(chunks)} chunks")
        
        # 批量嵌入
        texts = [c["text"] for c in chunks]
        embeddings = batch_embeddings(texts, verbose=verbose)
        
        # 組合 points
        points = []
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            if emb is None:
                stats["failed"] += 1
                continue
            
            point_id = generate_point_id(str(file_path), idx, chunk["text"])
            
            point = {
                "id": point_id,
                "vector": emb,
                "payload": {
                    "source": str(file_path.relative_to(source_dir)),
                    "full_path": str(file_path),
                    "chunk_index": idx,
                    "text": chunk["text"][:1000],  # 保留前1000字
                    "start_token": chunk["start"],
                    "end_token": chunk["end"],
                    "total_tokens": chunk.get("total_tokens", 0)
                }
            }
            points.append(point)
        
        # 批量上傳 Qdrant
        total_batches = (len(points) + BATCH_SIZE - 1) // BATCH_SIZE
        uploaded_batch = 0
        
        for batch_idx in range(total_batches):
            batch = points[batch_idx * BATCH_SIZE : (batch_idx + 1) * BATCH_SIZE]
            
            if qdrant_upsert_points(collection, batch):
                uploaded_batch += len(batch)
            else:
                stats["failed"] += len(batch)
        
        stats["total_chunks"] += len(chunks)
        stats["uploaded"] += uploaded_batch
        
        stats["details"].append({
            "file": str(file_path),
            "status": "success",
            "chunks": len(chunks),
            "uploaded": uploaded_batch
        })
        
        if verbose:
            print(f"  ✅ 上傳: {uploaded_batch}/{len(chunks)} chunks\n")
    
    return stats

# ── CLI Entry Point ───────────────────────────────────────────────────────────
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Document Ingestion")
    parser.add_argument(
        "--source", "-s",
        type=Path,
        default=Path(__file__).parent.parent / "knowledge",
        help="Source directory containing .md/.txt files"
    )
    parser.add_argument(
        "--collection", "-c",
        default=COLLECTION_NAME,
        help=f"Qdrant collection name (default: {COLLECTION_NAME})"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode (less output)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("RAG Pipeline - Document Ingestion (阿智產出)")
    print("=" * 60)
    print(f"Qdrant:  {QDRANT_HOST}")
    print(f"Ollama:  {OLLAMA_HOST}")
    print(f"Model:   {EMBED_MODEL}")
    print(f"Collection: {args.collection}")
    print(f"Source:  {args.source}")
    print("-" * 60)
    
    # 驗證 Ollama
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{OLLAMA_HOST}/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            if EMBED_MODEL not in models:
                print(f"⚠️  模型 {EMBED_MODEL} 未載入！")
                print(f"   現有模型: {', '.join(models[:5])}...")
    except Exception as e:
        print(f"⚠️  Ollama 連線失敗: {e}")
    
    # 驗證 Qdrant
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{QDRANT_HOST}/collections/{args.collection}")
            r.raise_for_status()
            info = r.json()["result"]
            vectors_conf = info["config"]["params"]["vectors"]
            print(f"✅ Qdrant collection '{args.collection}' 可用")
            print(f"   Vectors: {vectors_conf['size']} dims, {vectors_conf['distance']}")
    except Exception as e:
        print(f"⚠️  Qdrant collection '{args.collection}' 不存在或無法連線: {e}")
    
    print("-" * 60)
    
    # 執行攝入
    stats = ingest_documents(
        source_dir=args.source,
        collection=args.collection,
        verbose=not args.quiet
    )
    
    # 總結
    print("=" * 60)
    print("📊 攝入結果")
    print("=" * 60)
    print(f"  總分塊:   {stats['total_chunks']}")
    print(f"  上傳成功: {stats['uploaded']}")
    print(f"  失敗:     {stats['failed']}")
    print()
    
    if stats["uploaded"] > 0:
        print("✅ 攝入完成")
    else:
        print("⚠️  無資料上傳，請檢查錯誤")
        sys.exit(1)

if __name__ == "__main__":
    main()
