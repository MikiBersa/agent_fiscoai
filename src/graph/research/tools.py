from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from src.graph.research.estrazione import estrazione_circolari, estrazione_giurisprudenza, estrazione_risoluzione
from src.graph.research.state import Fonte, SearchState
from src.services.embeddings import EmbeddingAzure
from src.services.qdrant import QdrantHybridRetriever

LIMIT_QDRANT_TOP = 5


def get_qrant():
    azure_embedding = EmbeddingAzure()
    retriever = QdrantHybridRetriever(
        # qdrant_url="http://localhost:6333",
        qdrant_url="http://100.77.246.20:6333",
        provider_embedding=azure_embedding,
    )

    return retriever


def extractionFonte(formatted_results) -> list[Fonte]:
    nome_id = set()
    list_fonte = []
    for result in formatted_results:
        print("TIPO: ", result["tipo"])
        if result["tipo"] == "circolare":
            fonte: Fonte = estrazione_circolari(result)

            if fonte.id not in nome_id:
                nome_id.add(fonte.id)
                list_fonte.append(fonte)
            else:
                # TODO SE è DOPPIONE AGGIUNGEEREE NLE LIST
                for elem in list_fonte:
                    elem.ricostruito_testo.extend(fonte.ricostruito_testo)
        elif result["tipo"] == "giurisprudenza":
            fonte: Fonte = estrazione_giurisprudenza(result)

            if fonte.id not in nome_id:
                nome_id.add(fonte.id)
                list_fonte.append(fonte)
            else:
                # TODO SE è DOPPIONE AGGIUNGEEREE NLE LIST
                for elem in list_fonte:
                    elem.ricostruito_testo.extend(fonte.ricostruito_testo)

        elif result["tipo"] == "risoluzione":
            fonte: Fonte = estrazione_risoluzione(result)

            if fonte.id not in nome_id:
                nome_id.add(fonte.id)
                list_fonte.append(fonte)
            else:
                # TODO SE è DOPPIONE AGGIUNGEEREE NLE LIST
                for elem in list_fonte:
                    elem.ricostruito_testo.extend(fonte.ricostruito_testo)

        # if result["tipo"] == "circolare":

    return list_fonte


@tool(parse_docstring=True)
def rag_query(
    query: str,
    tipo: Literal["circolare", "giurisprudenza", "risoluzione", "all"],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> list:
    """Esegue una ricerca nella knowledge base circolari e di prassi (RAG) di Agenzia delle Entrate.

    Args:
        query: Testo della ricerca in linguaggio naturale (es. "detrazione ristrutturazioni edilizie").
        tipo: Tipologia di documenti su cui filtrare la ricerca. Usa 'circolare' per le circolari, 'giurisprudenza' per la giurisprudenza, 'risoluzione' per le risoluzioni e 'all' per cercare ovunque.

    Returns:
        I risultati della ricerca formattati come testo leggibile.
    """
    print("==== RICERCA RAG =====")
    print(query)

    retriever = get_qrant()

    # Configuro il filtro in base al tipo richiesto
    print("RICERCA CON TIPO: ", tipo)
    query_filter = None
    if tipo != "all":
        query_filter = retriever.build_filter(tipo=tipo)
    # query_filter = retriever.build_filter(tipo=tipo)

    # Eseguo la ricerca (ibrida densa + sparsa)
    try:
        search_results = retriever.search(
            query, query_filter=query_filter, limit=LIMIT_QDRANT_TOP
        )
        formatted_results = retriever.format_results(search_results)

        # TODO ANALIZZARE IL FORMATO ED ESPANDERE CON MONGODB
        list_fonte = extractionFonte(formatted_results)

        print("RITORNO ELEM")
    except Exception as e:
        print("ERRORE: ", str(e))
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        f"Errore durante la ricerca RAG: {str(e)}",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    # RITORNA IL TESTO TOTALE
    testo = ""

    print("LUNGHEZZA DELLE LISTE: ", len(list_fonte))

    for fonte in list_fonte:
        header = f"<Fonte id={fonte.id}, tipo={fonte.tipo}, data={fonte.data}>"
        corpo = "\n\n".join(fonte.ricostruito_testo)
        footer = "</Fonte>"

        testo += header + "\n" + corpo + "\n" + footer + "\n\n"

    print("RICOSTRUITO IL TESTO")
    print(len(testo))

    return Command(
        update={
            "list_fonte": list_fonte,
            "messages": [
                ToolMessage(
                    f"Informazioni trovate:\n{testo}", tool_call_id=tool_call_id
                )
            ],
        }
    )
