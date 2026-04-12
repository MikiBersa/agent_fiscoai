"""
Azure OpenAI - File Search completo (openai 2.3.x)
==================================================
1. Carica PDF da una cartella nel Vector Store
2. Ricerca sul Vector Store con Responses API
3. Restituisce chunk (testo + metadati + nome file) se disponibili

Dipendenze:
    pip install "openai==2.3.*" python-dotenv

File .env richiesto:
    AZURE_OPENAI_ENDPOINT=https://<tuo-endpoint>.openai.azure.com/
    AZURE_OPENAI_API_KEY=<tua-api-key>
    AZURE_OPENAI_DEPLOYMENT=<nome deployment Azure>
    AZURE_OPENAI_API_VERSION=2025-03-01-preview
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

AZURE_OPENAI_ENDPOINT = "https://llm-taxai.openai.azure.com/"
AZURE_OPENAI_API_KEY = "ChSYcqLmTJdqnEUtRQZ6JfkjZYCO9cfPzXlqcxdp4SLYnIydZGGXJQQJ99CCACYeBjFXJ3w3AAABACOGb6CU"
AZURE_OPENAI_API_VERSION = "2025-03-01-preview"
DEPLOYMENT = "gpt-4.1-mini"

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
)


# ---------------------------------------------------------------------------
# Strutture dati risultato
# ---------------------------------------------------------------------------

@dataclass
class ChunkResult:
    filename: str
    file_id: str
    score: float
    text: str
    attributes: dict = field(default_factory=dict)

    def __str__(self) -> str:
        sep = "─" * 60
        attrs = json.dumps(self.attributes, ensure_ascii=False) if self.attributes else "—"
        return (
            f"\n{sep}\n"
            f"📄 File      : {self.filename}\n"
            f"🆔 File ID   : {self.file_id}\n"
            f"⭐ Score     : {self.score:.4f}\n"
            f"🏷 Attributi : {attrs}\n"
            f"📝 Testo     :\n{self.text}\n"
            f"{sep}"
        )


@dataclass
class SearchResult:
    query: str
    answer: str
    chunks: list[ChunkResult]

    def print(self) -> None:
        print(f"\n{'═' * 60}")
        print(f"🔍 Query  : {self.query}")
        print(f"{'═' * 60}")
        print(f"\n💬 Risposta:\n{self.answer}")
        print(f"\n📚 Chunk sorgente ({len(self.chunks)} trovati):")
        for chunk in self.chunks:
            print(chunk)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_get(obj, name: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _as_dict(value) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 1. CARICAMENTO PDF DA CARTELLA
# ---------------------------------------------------------------------------

def upload_pdfs_to_vector_store(
    folder_path: str,
    vector_store_name: str = "PDF Knowledge Base",
    batch_size: int = 20,
) -> str:
    """
    Carica tutti i PDF da una cartella in un nuovo Vector Store.

    Nota:
    - Nella API moderna non faccio affidamento su chunking_strategy custom qui,
      perché il supporto effettivo può variare tra endpoint/versioni Azure.
    - Il servizio file search esegue parsing/chunking/embedding automaticamente.
    """
    folder = Path(folder_path)
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(f"Nessun PDF trovato in: {folder_path}")

    print(f"📁 Trovati {len(pdf_files)} PDF in '{folder_path}'")

    vector_store = client.vector_stores.create(name=vector_store_name)
    vs_id = vector_store.id
    print(f"✅ Vector Store creato: {vs_id} ('{vector_store_name}')")

    total_uploaded = 0

    for i in range(0, len(pdf_files), batch_size):
        batch = pdf_files[i:i + batch_size]
        print(f"\n📤 Batch {i // batch_size + 1}: caricamento {len(batch)} file...")

        for pdf_path in batch:
            with open(pdf_path, "rb") as f:
                uploaded = client.vector_stores.files.upload_and_poll(
                    vector_store_id=vs_id,
                    file=f,
                )

            file_id = _safe_get(uploaded, "id", "")
            status = _safe_get(uploaded, "status", "unknown")
            print(f"   ↑ {pdf_path.name} → {file_id} | status={status}")

            if status in {"completed", "processed", "succeeded"}:
                total_uploaded += 1

    vs_info = client.vector_stores.retrieve(vs_id)
    usage_bytes = _safe_get(vs_info, "usage_bytes", 0) or 0
    size_mb = usage_bytes / (1024 * 1024)

    print(
        f"\n🏁 Upload completato: {total_uploaded} file, "
        f"~{size_mb:.1f} MB nel Vector Store '{vs_id}'"
    )
    return vs_id


# ---------------------------------------------------------------------------
# 2 & 3. RICERCA + CHUNK CON TESTO
# ---------------------------------------------------------------------------

def hybrid_search(
    query: str,
    vector_store_id: str,
    max_chunks: int = 10,
    score_threshold: Optional[float] = None,
    system_prompt: str = (
        "Sei un assistente preciso. Rispondi basandoti solo sui documenti forniti. "
        "Se non trovi base sufficiente nei documenti, dillo esplicitamente."
    ),
) -> SearchResult:
    """
    Esegue ricerca tramite Responses API + file_search.

    Nota:
    - Il file search combina già ricerca keyword e semantica lato servizio.
    - Non espongo text_weight / embedding_weight perché non risultano parametri
      affidabili/supported nella forma moderna della richiesta.
    """
    print(f"\n🔍 Ricerca: '{query[:120]}{'...' if len(query) > 120 else ''}'")

    tool = {
        "type": "file_search",
        "vector_store_ids": [vector_store_id],
        "max_num_results": max_chunks,
        "ranking_options": {
            "ranker": "auto",
            "score_threshold": score_threshold if score_threshold is not None else 0.0,
        },
    }

    response = client.responses.create(
        model=DEPLOYMENT,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        tools=[tool],
        include=["file_search_call.results"],
    )

    answer = getattr(response, "output_text", "") or ""
    raw_chunks = []

    for output in getattr(response, "output", []) or []:
        if _safe_get(output, "type") == "file_search_call":
            results = _safe_get(output, "results", []) or []
            raw_chunks.extend(results)

    chunks: list[ChunkResult] = []

    for r in raw_chunks:
        score = _safe_get(r, "score", 0.0) or 0.0
        if score_threshold is not None and score < score_threshold:
            continue

        chunk = ChunkResult(
            filename=_safe_get(r, "filename", "sconosciuto"),
            file_id=_safe_get(r, "file_id", ""),
            score=score,
            text=_safe_get(r, "text", "") or "",
            attributes=_as_dict(_safe_get(r, "attributes", {})),
        )
        chunks.append(chunk)

    chunks.sort(key=lambda c: c.score, reverse=True)

    return SearchResult(query=query, answer=answer, chunks=chunks)


# ---------------------------------------------------------------------------
# Assistants API - fallback legacy
# ---------------------------------------------------------------------------

def search_with_assistants_api(
    query: str,
    vector_store_id: str,
    max_chunks: int = 10,
) -> dict:
    """
    Fallback legacy per ambienti Azure che espongono ancora Assistants beta.
    """
    assistant = client.beta.assistants.create(
        name="TempSearchAssistant",
        model=DEPLOYMENT,
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store_id],
                "max_num_results": max_chunks,
            }
        },
    )

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=query,
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    result = {"answer": "", "annotations": []}

    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        for msg in messages.data:
            if msg.role != "assistant":
                continue

            content = msg.content[0].text
            answer_text = content.value

            for idx, annotation in enumerate(content.annotations):
                placeholder = annotation.text
                answer_text = answer_text.replace(placeholder, f"[{idx}]")

                file_citation = getattr(annotation, "file_citation", None)
                if file_citation:
                    try:
                        file_info = client.files.retrieve(file_citation.file_id)
                        filename = getattr(file_info, "filename", "sconosciuto")
                    except Exception:
                        filename = "sconosciuto"

                    result["annotations"].append({
                        "index": idx,
                        "file_id": file_citation.file_id,
                        "filename": filename,
                        "placeholder": placeholder,
                    })

            result["answer"] = answer_text
            break

    try:
        client.beta.threads.delete(thread.id)
    except Exception:
        pass

    try:
        client.beta.assistants.delete(assistant.id)
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Utilità
# ---------------------------------------------------------------------------

def list_vector_stores() -> None:
    stores = client.vector_stores.list()

    print("\n📦 Vector Store esistenti:")
    for vs in getattr(stores, "data", []) or []:
        usage_bytes = _safe_get(vs, "usage_bytes", 0) or 0
        size_mb = usage_bytes / (1024 * 1024)
        status = _safe_get(vs, "status", "unknown")
        name = _safe_get(vs, "name", "")
        print(f"  • {vs.id} | '{name}' | {size_mb:.1f} MB | status: {status}")


def delete_vector_store(vector_store_id: str) -> None:
    files = client.vector_stores.files.list(vector_store_id=vector_store_id)

    for f in getattr(files, "data", []) or []:
        file_id = _safe_get(f, "id")
        if file_id:
            try:
                client.files.delete(file_id)
            except Exception:
                pass

    client.vector_stores.delete(vector_store_id)
    print(f"🗑 Vector Store '{vector_store_id}' eliminato.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    PDF_FOLDER = "./docs/2024"

    print("=" * 60)
    print("STEP 1 — Caricamento PDF nel Vector Store")
    print("=" * 60)

    """

    vs_id = upload_pdfs_to_vector_store(
        folder_path=PDF_FOLDER,
        vector_store_name="prova-openai-2-3",
        batch_size=10,
    )

    """

    # print(f"\n✅ Vector Store pronto: {vs_id}")

    vs_id = "vs_BNsrYLnMG9OCCUecr9m7dnEM"

    print(f"\n✅ Vector Store pronto: {vs_id}")

    print("\n" + "=" * 60)
    print("STEP 2 — Ricerca + Recupero Chunk")
    print("=" * 60)

    query = """
    [ALF A], di seguito anche istante, fa presente quanto nel prosieguo sinteticamente
riportato:
­ di aver presentato, in data [...] 2018 e [...] 2020, due successive domande di
ammissione a concordato preventivo, procedure entrambe estinte;
­ di aver presentato, in data [...] 2021, un piano di ristrutturazione del debito,
depositato presso il registro delle imprese, ai sensi dell'articolo 67, comma 3, del Regio
Decreto 16 marzo 1942, n. 267 (di seguito, Legge Fallimentare);
Pagina 2 di 7
­ di aver venduto, in data [...] 2022, immobili al prezzo di euro [...], al fine di
far fronte al debito ristrutturato (tra cui euro [...] in favore di Agenzia delle entrateRiscossione);
­ successivamente, confidando su tale disponibilità, di aver presentato domanda di
definizione agevolata (c.d. ''rottamazione quater''), in base all'articolo 1, commi da 231 a
252 della legge 29 dicembre 2022, n. 197, accolta da Agenzia delle entrate­Riscossione
in data 7 agosto 2023;
­ di non essere riuscita a versare tempestivamente, ovvero entro il 31 ottobre 2023,
la prima rata della definizione agevolata, a causa della tardiva approvazione del piano di
riparto, che ha impedito la piena utilizzabilità delle somme già incassate a seguito della
predetta vendita di immobili;
­ di aver, conseguentemente, versato l'importo di euro [...] in favore di Agenzia
delle entrate­Riscossione, in ritardo, solo a seguito dell'esecutività del predetto piano di
riparto, avvenuta in data [...] novembre 2023, nel cui verbale di udienza si afferma che
« [ALF A] ha aderito alla rottamazione quater e che dunque le somme di cui al riparto
sono oggetto di tale rottamazione».
Ciò premesso, l'istante chiede di sapere «se sia possibile imputare il versamento
dell'importo di euro [...] (riferito al debito nei confronti dell'Agenzia entrateRiscossione),
alle prime due rate necessarie per la definizione agevolata di cui alla
c.d. rottamazione quater; definizione agevolata dalla quale la società è decaduta per
omesso versamento della prima rata causato dalla assoluta carenza di liquidità a sé non
imputabile [...]».
    """

    result = hybrid_search(
        query=query,
        vector_store_id=vs_id,
        max_chunks=5,
        score_threshold=0.0,
    )
    result.print()

    print("\n" + "=" * 60)
    print("Vector Stores")
    print("=" * 60)
    list_vector_stores()

    # delete_vector_store(vs_id)