from typing import Annotated, Literal

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.graph.research.state import SearchState
from src.services.embeddings import EmbeddingAzure
from src.services.qdrant import QdrantHybridRetriever

LIMIT_QDRANT_TOP = 10


def get_qrant():
    azure_embedding = EmbeddingAzure()
    retriever = QdrantHybridRetriever(
        qdrant_url="http://localhost:6333",
        provider_embedding=azure_embedding,
    )

    return retriever


def extractionFonte(formatted_results):
    for result in formatted_results:
        pass


@tool(parse_docstring=True)
def rag_query(
    query: str,
    tipo: Literal["circolare", "all"],
    state: Annotated[SearchState, InjectedState],
) -> str:
    """Esegue una ricerca nella knowledge base circolari e di prassi (RAG) di Agenzia delle Entrate.

    Args:
        query: Testo della ricerca in linguaggio naturale (es. "detrazione ristrutturazioni edilizie").
        tipo: Tipologia di documenti su cui filtrare la ricerca. Usare 'all' per cercare ovunque.

    Returns:
        I risultati della ricerca formattati come testo leggibile.
    """
    retriever = get_qrant()

    # Configuro il filtro in base al tipo richiesto
    query_filter = None
    if tipo != "all":
        query_filter = retriever.build_filter(tipo=tipo)

    # Eseguo la ricerca (ibrida densa + sparsa)
    try:
        search_results = retriever.search(
            query, query_filter=query_filter, limit=LIMIT_QDRANT_TOP
        )
        formatted_results = retriever.format_results(search_results)

        # TODO ANALIZZARE IL FORMATO ED ESPANDERE CON MONGODB
    except Exception as e:
        return f"Errore durante la ricerca RAG: {str(e)}"

    if not formatted_results:
        return f"Nessun risultato trovato nella knowledge base per la query '{query}' con filtro tipo: '{tipo}'."

    return None
