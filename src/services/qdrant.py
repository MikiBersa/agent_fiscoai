from __future__ import annotations

import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv

load_dotenv()

import uuid
from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient, models

from src.services.embeddings import EmbeddingAzure


class QdrantHybridRetriever:
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "norme",
        provider_embedding: EmbeddingAzure = None,
        dense_vector_name: str = "text-embedding-3-small",
        sparse_vector_name: str = "keywords_search",
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self.collection_name = collection_name
        self.dense_vector_name = dense_vector_name
        self.sparse_vector_name = sparse_vector_name
        self.provider_embedding = provider_embedding

        self.qdrant = QdrantClient(url=qdrant_url, timeout=300)

    # =========================
    # INTERNAL HELPERS
    # =========================
    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.provider_embedding.calculate_emebddings(texts=texts)

    def _to_iso_datetime(self, value: str | datetime) -> str:
        if isinstance(value, datetime):
            iso_str = value.isoformat()
            # Qdrant richiede il formato RFC3339, quindi l'offset del fuso orario è obbligatorio.
            # Se la data è "naive" (senza fuso orario), aggiungiamo "Z" (UTC).
            # if value.tzinfo is None:
            #    iso_str += "Z"
            return iso_str

        if isinstance(value, str):
            # Se è una stringa proviamo a capire se le manca l'offset timezone
            if not value.endswith("Z") and not ("+" in value[-6:] or "-" in value[-6:]):
                value += "Z"
            return value

        return value

    def _normalize_doc(self, doc: dict[str, Any]) -> dict[str, Any]:
        required = ["id", "id_padre", "text", "data", "tipo", "name_id"]
        for key in required:
            if key not in doc:
                raise ValueError(f"Campo mancante nel documento: {key}")

        return {
            "id": str(doc["id"]),
            "id_padre": str(doc["id_padre"]),
            "text": str(doc["text"]),
            "data": self._to_iso_datetime(doc["data"]),
            "tipo": str(doc["tipo"]),
            "name_id": str(doc["name_id"]),
        }

    def _build_points(self, docs: list[dict[str, Any]]) -> list[models.PointStruct]:
        normalized_docs = [self._normalize_doc(doc) for doc in docs]
        texts = [doc["text"] for doc in normalized_docs]
        dense_vectors = self._embed_texts(texts)

        points: list[models.PointStruct] = []
        for doc, dense_vector in zip(normalized_docs, dense_vectors):
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, doc["text"])),
                    vector={
                        self.dense_vector_name: dense_vector,
                        self.sparse_vector_name: models.Document(
                            text=doc["text"],
                            model="qdrant/bm25",
                        ),
                    },
                    payload={
                        "id": doc["id"],
                        "id_padre": doc["id_padre"],
                        "data": doc["data"],
                        "tipo": doc["tipo"],
                        "name_id": doc["name_id"],
                    },
                )
            )
        return points

    # =========================
    # PUBLIC: INSERT / UPSERT
    # =========================
    def add_documents(self, docs: list[dict[str, Any]], wait: bool = True) -> None:
        batch_size = 500

        for i in range(0, len(docs), batch_size):
            points = self._build_points(docs[i : i + batch_size])

            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=False,
            )

            print("Arrivati: ", i)

    def add_document(self, doc: dict[str, Any], wait: bool = True) -> None:
        self.add_documents([doc], wait=wait)

    # =========================
    # PUBLIC: FILTERS
    # =========================
    def build_filter(
        self,
        *,
        tipo: str | list[str] | None = None,
        id_padre: str | list[str] | None = None,
        point_id: str | list[str] | None = None,
        data_gte: str | datetime | None = None,
        data_lte: str | datetime | None = None,
        name_id_text: str | None = None,
    ) -> models.Filter | None:
        must: list[Any] = []

        if tipo is not None:
            if isinstance(tipo, list):
                must.append(
                    models.FieldCondition(
                        key="tipo",
                        match=models.MatchAny(any=tipo),
                    )
                )
            else:
                must.append(
                    models.FieldCondition(
                        key="tipo",
                        match=models.MatchValue(value=tipo),
                    )
                )

        if id_padre is not None:
            if isinstance(id_padre, list):
                must.append(
                    models.FieldCondition(
                        key="id_padre",
                        match=models.MatchAny(any=id_padre),
                    )
                )
            else:
                must.append(
                    models.FieldCondition(
                        key="id_padre",
                        match=models.MatchValue(value=id_padre),
                    )
                )

        if point_id is not None:
            if isinstance(point_id, list):
                must.append(
                    models.FieldCondition(
                        key="id",
                        match=models.MatchAny(any=point_id),
                    )
                )
            else:
                must.append(
                    models.FieldCondition(
                        key="id",
                        match=models.MatchValue(value=point_id),
                    )
                )

        if data_gte is not None or data_lte is not None:
            must.append(
                models.FieldCondition(
                    key="data",
                    range=models.DatetimeRange(
                        gte=self._to_iso_datetime(data_gte) if data_gte else None,
                        lte=self._to_iso_datetime(data_lte) if data_lte else None,
                    ),
                )
            )

        if name_id_text is not None:
            must.append(
                models.FieldCondition(
                    key="name_id",
                    match=models.MatchText(text=name_id_text),
                )
            )

        if not must:
            return None

        return models.Filter(must=must)

    # =========================
    # PUBLIC: SEARCH
    # =========================
    def semantic_search(
        self,
        query_text: str,
        limit: int = 10,
        query_filter: models.Filter | None = None,
        with_payload: bool = True,
    ):
        query_vector = self._embed_texts([query_text])[0]

        return self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using=self.dense_vector_name,
            limit=limit,
            query_filter=query_filter,
            with_payload=with_payload,
        )

    def bm25_search(
        self,
        query_text: str,
        limit: int = 10,
        query_filter: models.Filter | None = None,
        with_payload: bool = True,
    ):
        return self.qdrant.query_points(
            collection_name=self.collection_name,
            query=models.Document(
                text=query_text,
                model="qdrant/bm25",
            ),
            using=self.sparse_vector_name,
            limit=limit,
            query_filter=query_filter,
            with_payload=with_payload,
        )

    def hybrid_search(
        self,
        query_text: str,
        limit: int = 10,
        prefetch_limit: int = 30,
        query_filter: models.Filter | None = None,
        with_payload: bool = True,
    ):
        query_vector = self._embed_texts([query_text])[0]

        return self.qdrant.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=query_vector,
                    using=self.dense_vector_name,
                    limit=prefetch_limit,
                ),
                models.Prefetch(
                    query=models.Document(
                        text=query_text,
                        model="qdrant/bm25",
                    ),
                    using=self.sparse_vector_name,
                    limit=prefetch_limit,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            limit=limit,
            query_filter=query_filter,
            with_payload=with_payload,
        )

    # =========================
    # PUBLIC: GENERIC SEARCH
    # =========================
    def search(
        self,
        query_text: str,
        mode: str = "hybrid",
        limit: int = 20, # 10
        prefetch_limit: int = 40, # 30
        query_filter: models.Filter | None = None,
        with_payload: bool = True,
    ):
        mode = mode.lower()

        if mode == "semantic":
            return self.semantic_search(
                query_text=query_text,
                limit=limit,
                query_filter=query_filter,
                with_payload=with_payload,
            )

        if mode == "bm25":
            return self.bm25_search(
                query_text=query_text,
                limit=limit,
                query_filter=query_filter,
                with_payload=with_payload,
            )

        if mode == "hybrid":
            return self.hybrid_search(
                query_text=query_text,
                limit=limit,
                prefetch_limit=prefetch_limit,
                query_filter=query_filter,
                with_payload=with_payload,
            )

        raise ValueError("mode deve essere uno tra: 'semantic', 'bm25', 'hybrid'")

    # =========================
    # PUBLIC: UTILS
    # =========================
    @staticmethod
    def format_results(result, text_max_len: int = 250) -> list[dict[str, Any]]:
        formatted = []

        for point in result.points:
            payload = point.payload or {}
            text = payload.get("text", "")
            formatted.append(
                {
                    "score": point.score,
                    "id": payload.get("id"),
                    "id_padre": payload.get("id_padre"),
                    "tipo": payload.get("tipo"),
                    "data": payload.get("data"),
                    "name_id": payload.get("name_id"),
                    "text": text[:text_max_len]
                    + ("..." if len(text) > text_max_len else ""),
                }
            )

        return formatted

    @staticmethod
    def print_results(
        result, title: str = "RISULTATI", text_max_len: int = 250
    ) -> None:
        print(f"\n=== {title} ===")
        for i, point in enumerate(result.points, start=1):
            payload = point.payload or {}
            text = payload.get("text", "")
            short_text = text[:text_max_len] + (
                "..." if len(text) > text_max_len else ""
            )

            print(f"\n[{i}] score={point.score}")
            print(f"id       : {payload.get('id')}")
            print(f"id_padre : {payload.get('id_padre')}")
            print(f"tipo     : {payload.get('tipo')}")
            print(f"data     : {payload.get('data')}")
            print(f"name_id  : {payload.get('name_id')}")
            print(f"text     : {short_text}")
            print(f"name_id  : {payload.get('name_id')}")
            print(f"text     : {short_text}")
            print(f"text     : {short_text}")


if __name__ == "__main__":
    azure_embedding = EmbeddingAzure()
    # qdrant_url = "http://192.168.178.29:6333"
    qdrant_url = "http://100.77.246.20:6333"
    retriever = QdrantHybridRetriever(
        qdrant_url=qdrant_url, provider_embedding=azure_embedding
    )

    """
    result = retriever.search("ciao")

    print(result)
    """

    query = "Vorrei registrare un contratto di locazione ad uso abitativo in cedolare secca: il contratto decorre dal 01/01/2025 per cui la tardiva registrazione è superiore a 30 giorni. A quanto ammonta la sanzione? Grazie"

    build_filter = retriever.build_filter(
        tipo="norma",
        # data_gte=datetime(2020, 1, 1),
        # data_lte=datetime(2024, 12, 31),
        # name_id_text = "ADE_C2-E_D14-03-2025" # MATCH ESATTO TESTO
    )

    # TODO MEGLIO FARE LE RICERCHE IN MANIERA SEPARATA
    result = retriever.search(query, query_filter=build_filter)

    for elem in result.points:
        print(elem.payload["name_id"])
