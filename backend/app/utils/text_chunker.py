from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

CHUNK_SIZE = 200
CHUNK_OVERLAP = 30
CHUNK_SEPARATORS = ["\n\n", "\n", "。", "；", "，", " ", ""]

_splitter = None


def _get_splitter():
    global _splitter
    if _splitter is None:
        _splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=CHUNK_SEPARATORS,
            length_function=len,
        )
    return _splitter


def split_text(text: str) -> List[Dict[str, any]]:
    if not text or not text.strip():
        return []

    text = text.strip()
    splitter = _get_splitter()

    chunks = splitter.split_text(text)

    result = []
    for idx, chunk_text in enumerate(chunks):
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue
        result.append({
            "chunk_index": idx,
            "content": chunk_text,
            "char_count": len(chunk_text),
        })

    logger.debug(f"Split text ({len(text)} chars) into {len(result)} chunks")
    return result


def batch_split_documents(documents: List[Dict[str, any]]) -> List[Dict[str, any]]:
    all_chunks = []
    for doc in documents:
        doc_id = doc.get("doc_id", doc.get("id"))
        content = doc.get("content", "")
        category = doc.get("category", "")
        title = doc.get("title", "")

        chunks = split_text(content)
        if not chunks:
            all_chunks.append({
                "doc_id": doc_id,
                "chunk_index": 0,
                "content": content[:2000],
                "category": category,
                "title": title,
                "char_count": len(content),
            })
            continue

        for chunk in chunks:
            all_chunks.append({
                "doc_id": doc_id,
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "category": category,
                "title": title,
                "char_count": chunk["char_count"],
            })

    logger.info(f"Batch split {len(documents)} documents into {len(all_chunks)} chunks")
    return all_chunks
