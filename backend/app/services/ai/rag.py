"""Lightweight RAG knowledge base using simple TF-IDF style scoring (FAISS optional)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + size])
        if chunk.strip():
            chunks.append(chunk.strip())
        i += max(1, size - overlap)
    return chunks or [text]


class KnowledgeRAG:
    def __init__(self):
        self.store_path = Path(settings.vector_store_dir)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.store_path / "kb_index.json"
        self.documents: list[dict] = []
        self._load()

    def _load(self):
        if self.index_file.exists():
            self.documents = json.loads(self.index_file.read_text(encoding="utf-8"))
        else:
            self.documents = []
            self._seed_defaults()

    def _save(self):
        self.index_file.write_text(json.dumps(self.documents, indent=2), encoding="utf-8")

    def _seed_defaults(self):
        seeds = [
            {
                "title": "FDA 21 CFR 211.198 – Complaint Files",
                "doc_type": "FDA",
                "content": (
                    "Written procedures describing the handling of all written and oral complaints "
                    "regarding a drug product shall be established and followed. A written record of "
                    "each complaint shall be maintained in a file designated for drug product complaints. "
                    "The record shall include name and strength of drug, lot number, name of complainant, "
                    "nature of complaint, and reply to complainant. Investigation of complaints involving "
                    "possible failure of a drug product to meet any of its specifications shall be conducted."
                ),
            },
            {
                "title": "WHO GMP – Product Quality Complaints",
                "doc_type": "WHO_GMP",
                "content": (
                    "All quality related complaints should be recorded and investigated according to written procedures. "
                    "A person responsible for handling complaints should be designated. Trends should be reviewed. "
                    "Where a product defect is discovered, consideration should be given to whether other batches should "
                    "be checked and whether a recall is needed."
                ),
            },
            {
                "title": "SOP – Capsule Discoloration Investigation",
                "doc_type": "SOP",
                "content": (
                    "For capsule discoloration complaints: quarantine batch, pull retain samples, perform visual inspection, "
                    "moisture content analysis, dissolution, assay, and packaging integrity (leak) testing. "
                    "Review packaging line sealer calibration logs and warehouse humidity records. "
                    "Assess related batches on same packaging line within ±7 days."
                ),
            },
            {
                "title": "CAPA Template – Packaging Integrity",
                "doc_type": "CAPA_TEMPLATE",
                "content": (
                    "Corrective: Quarantine affected batch; replace defective packaging; rework only if justified. "
                    "Preventive: Calibrate heat sealers per PM schedule; increase leak-test sampling; RH monitoring "
                    "alarms; operator refresher training; effectiveness check at 90 days via complaint trend review."
                ),
            },
        ]
        for s in seeds:
            self.add_document(s["title"], s["doc_type"], s["content"])

    def add_document(self, title: str, doc_type: str, content: str, filename: str = "") -> int:
        chunks = _chunk_text(content)
        doc_id = len(self.documents) + 1
        for i, chunk in enumerate(chunks):
            self.documents.append(
                {
                    "id": f"{doc_id}-{i}",
                    "doc_id": doc_id,
                    "title": title,
                    "doc_type": doc_type,
                    "filename": filename,
                    "chunk_index": i,
                    "content": chunk,
                    "tokens": _tokenize(chunk),
                }
            )
        self._save()
        return len(chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        q_tokens = set(_tokenize(query))
        if not q_tokens:
            return []
        scored = []
        for doc in self.documents:
            overlap = len(q_tokens & set(doc.get("tokens") or _tokenize(doc["content"])))
            if overlap:
                scored.append({**doc, "score": overlap / max(len(q_tokens), 1)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [
            {
                "title": s["title"],
                "doc_type": s["doc_type"],
                "content": s["content"],
                "score": round(s["score"], 3),
            }
            for s in scored[:top_k]
        ]

    def answer(self, query: str) -> dict:
        hits = self.search(query, top_k=4)
        if not hits:
            return {
                "answer": "No relevant documents found in the knowledge base. Upload SOPs, FDA guidelines, or CAPA templates.",
                "sources": [],
            }
        context = "\n\n".join(f"[{h['title']}]\n{h['content']}" for h in hits)
        answer = (
            f"Based on company knowledge base documents:\n\n{hits[0]['content'][:500]}\n\n"
            f"Related sources: {', '.join(h['title'] for h in hits)}"
        )
        return {"answer": answer, "sources": hits, "context": context}


_rag: Optional[KnowledgeRAG] = None


def get_rag() -> KnowledgeRAG:
    global _rag
    if _rag is None:
        _rag = KnowledgeRAG()
    return _rag
