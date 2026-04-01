import os
import sys
import warnings

# Suppress Pydantic V1 migration warnings in Python 3.14+
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Pydantic V1 functionality.*"
)

# Add the project root to sys.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from dotenv import load_dotenv

load_dotenv()

from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from src.graph.research.estrazione import estrazione_circolari, estrazione_giurisprudenza, estrazione_risoluzione, estrazione_provvedimento, estrazione_norma_specifica
from src.graph.research.state import Fonte, SearchState
from src.services.embeddings import EmbeddingAzure
from src.services.qdrant import QdrantHybridRetriever
from src.graph.research.content_intent import content_intent
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

LIMIT_QDRANT_TOP = 10


def get_qrant():
    azure_embedding = EmbeddingAzure()
    retriever = QdrantHybridRetriever(
        # qdrant_url="http://localhost:6333",
        qdrant_url="http://100.77.246.20:6333",
        provider_embedding=azure_embedding,
    )

    return retriever


def extractionFonte(formatted_results, list_fonte: list[Fonte]) -> list[Fonte]:
    nome_id = set([fonte.id for fonte in list_fonte])
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

        elif result["tipo"] == "provvedimento":
            fonte: Fonte = estrazione_provvedimento(result)

            if fonte.id not in nome_id:
                nome_id.add(fonte.id)
                list_fonte.append(fonte)
            else:
                # TODO SE è DOPPIONE AGGIUNGEEREE NLE LIST
                for elem in list_fonte:
                    elem.ricostruito_testo.extend(fonte.ricostruito_testo)

        # if result["tipo"] == "circolare":

    return list_fonte


# @tool(parse_docstring=True)
def _rag_query_implement(
    query: str,
    tipo: Literal["circolare", "giurisprudenza", "risoluzione", "all"],
    state: Annotated[SearchState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> list:
    """Esegue una ricerca nella knowledge base circolari e di prassi (RAG) di Agenzia delle Entrate.

    Args:
        query: Testo della ricerca in linguaggio naturale (es. "detrazione ristrutturazioni edilizie").
        tipo: Tipologia di documenti su cui filtrare la ricerca. Usa 'circolare' per le circolari, 'giurisprudenza' per la giurisprudenza, 'risoluzione' per le risoluzioni e 'all' per cercare ovunque.

    Returns:
        I risultati della ricerca formattati come testo leggibile.
    """
    list_fonte = state["list_fonte"]
    print("==== RICERCA RAG =====")
    print(query)

    retriever = get_qrant()

    # INSERIRE LA LOGICA PER ESTRARRE ANNO, NUMERO E ARTICOLO DALLA QUERY
    citazione_fonte = content_intent.invoke({"text": query})
    print("CITAZIONE FONTE: ", citazione_fonte)

    if citazione_fonte.check_presenza:
        ricerca_norma = _rag_query_norma_specifica(citazione_fonte.anno_norma, citazione_fonte.numero_norma, citazione_fonte.articolo_norma, state, tool_call_id)
        liste = ricerca_norma.update["list_fonte"]

        for elem in liste:  
            if elem.id not in [fonte.id for fonte in list_fonte]:
                list_fonte.append(elem)

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

        # ANALIZZARE IL FORMATO ED ESPANDERE CON MONGODB
        list_fonte = extractionFonte(formatted_results, list_fonte)

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
        #corpo = "\n\n".join(fonte.ricostruito_testo)
        #footer = "</Fonte>"

        # testo += header + "\n" + corpo + "\n" + footer + "\n\n"
        testo += header + "\n"

    print("RICOSTRUITO IL TESTO")
    print(len(testo))

    # TODO TOGLIERE TUTTI I MESSAGES
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

@tool(parse_docstring=True)
def rag_query(
    query: str,
    tipo: Literal["circolare", "giurisprudenza", "risoluzione", "all"],
    state: Annotated[SearchState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> list:
    """Esegue una ricerca nella knowledge base normativa e di prassi (RAG) di Agenzia delle Entrate.

    Args:
        query: Testo della ricerca in linguaggio naturale (es. "detrazione ristrutturazioni edilizie"). Riporta il task da eseguire la query deve essere almeno dai 3 alle 5 frasi per ottimizzare la ricerca ad ambedding e keyword.
        tipo: Tipologia di documenti su cui filtrare la ricerca. Usa 'circolare' per le circolari, 'giurisprudenza' per la giurisprudenza, 'risoluzione' per le risoluzioni e 'all' per cercare ovunque.

    Returns:
        I risultati della ricerca formattati come testo leggibile.
    """
    return _rag_query_implement(query, tipo, state, tool_call_id)

def _rag_query_norma_specifica(anno: str, numero: str, articolo: str, state: Annotated[SearchState, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> list:
    list_fonte = state["list_fonte"]

    elem: Fonte = estrazione_norma_specifica(anno, numero, articolo)
    list_fonte.append(elem)

    testo = ""

    if elem is None:
        return Command(
            update={
                "list_fonte": list_fonte,
                "messages": [
                    ToolMessage(
                        f"Non ho trovato la norma specificata: {anno} {numero} {articolo}", tool_call_id=tool_call_id
                    )
                ],
            }
        )

    for fonte in list_fonte:
        header = f"<Fonte id={fonte.id}, tipo={fonte.tipo}, data={fonte.data}>"
        #corpo = "\n\n".join(fonte.ricostruito_testo)
        #footer = "</Fonte>"

        # testo += header + "\n" + corpo + "\n" + footer + "\n\n"
        testo += header + "\n"
    
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

# TODO FARE RICERCA EFFETTIVA CON NOME_ID
@tool(parse_docstring=True)
def rag_query_norma_specifica(
    anno: str,
    numero: str,
    articolo: str,
    state: Annotated[SearchState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> list:
    """Esegue una ricerca specifica sulle norme italiane tramite anno, numero e articolo.
    Da usare quando si vuole fare una ricerca di una norma specifica ed estrapolare intero testo.

    Args:
        anno: Anno di riferimento della norma.
        numero: Numero della norma.
        articolo: Articolo della norma.

    Returns:
        I risultati della ricerca formattati come testo leggibile.
    """
    print("RICERCA NORMA SPECIFICA")
    print("ANNO: ", anno)
    print("NUMERO: ", numero)
    print("ARTICOLO: ", articolo)
    print("/"*80)

    return _rag_query_norma_specifica(anno, numero, articolo, state, tool_call_id)


def summary_writing(
    list_fonte: list[Fonte],
) -> str:
    """Questo tool fa un riassunto dettagliato delle informazioni trovate durate la richerca.

    Args:

    Returns:
        I risultati della ricerca formattati come testo leggibile.
    """

    print("==== SUMMARY WRITING ====")
    

    # list_fonte = state["list_fonte"]
    testo = ""

    for fonte in list_fonte:
        header = f"<Fonte id={fonte.id}, tipo={fonte.tipo}, data={fonte.data}>"
        corpo = "\n\n".join(fonte.ricostruito_testo)
        footer = "</Fonte>"

        testo += header + "\n" + corpo + "\n" + footer + "\n\n"
    
    summary_prompt = ChatPromptTemplate.from_template(
        """
        Sei un esperto di diritto tributario italiano.
        Il tuo compito è fare un riassunto dettagliato delle informazioni trovate durate la richerca.
        Ripoorta le infromazioni riassumento quindi estrarre i concetti più importanti.
        
        <TESTO DA ANALIZZARE>
        {testo}
        </TESTO DA ANALIZZARE>
        """
    )

    summary_agent = summary_prompt | AzureChatOpenAI(
        azure_deployment="gpt-4.1-mini",
        api_version="2024-12-01-preview",
        max_tokens=1000,
    )

    summary = summary_agent.invoke({"testo": testo})

    return summary.content

def summary_writing_summary(
    summary: str,
) -> str:
    """Questo tool fa un riassunto dettagliato delle informazioni trovate durate la richerca.

    Args:

    Returns:
        I risultati della ricerca formattati come testo leggibile.
    """

    print("==== SUMMARY WRITING SUMMARY ====")

    
    summary_prompt = ChatPromptTemplate.from_template(
        """
        Sei un esperto di diritto tributario italiano.
        Il tuo compito è fare un riassunto dettagliato delle informazioni trovate durate la richerca.
        Ripoorta le infromazioni riassumento quindi estrarre i concetti più importanti.
        
        <TESTO DA ANALIZZARE>
        {testo}
        </TESTO DA ANALIZZARE>
        """
    )

    summary_agent = summary_prompt | AzureChatOpenAI(
        azure_deployment="gpt-4.1-mini",
        api_version="2024-12-01-preview",
        max_tokens=1000,
    )

    summary = summary_agent.invoke({"testo": summary})

    return summary.content

if __name__ == "__main__":
    # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

    result = _rag_query_implement(
        """L'Istante, condomino di un ''condominio minimo'' situato nel territorio della
Regione X composto da n. 5 unità immobiliari, unitamente agli altri proprietari
e comodatari, ha deliberato e incaricato una ditta edile di effettuare interventi di
efficientamento energetico di cui all'articolo 119 del decreto legge n. 34 del 2020 (cd.
Superbonus), con conseguente presentazione della CILAS in data 15 aprile 2022.
L'Istante rappresenta che intende sostituire (come intervento ''trainato'') le
finestre e persiane ''ad arco'' dell'intero edificio con il mantenimento della stessa forma e
che, al momento della firma del contratto di appalto avvenuto ad aprile 2022, il prezzario
della Regione X non contemplava tale tipologia di infisso e, pertanto, è stato utilizzato
il prezzario della ''vicina'' Regione Y edizione 2021 che, invece, la prevedeva.
L'Istante fa presente che la sostituzione delle finestre e persiane è attualmente in
corso e che, nel frattempo, la Regione X ha aggiornato il prezzario includendovi anche
i prezzi riferiti alla sostituzione delle persiane e delle finestre ''ad arco''.
Con documentazione integrativa l'Istante ha specificato che per l'intervento
complessivo prospettato è stato completato il primo SAL, in data 2 maggio 2023, e che
il secondo e ultimo SAL, nel quale confluirà anche l'intervento trainato di sostituzione
delle finestre e persiane, è in corso. Lo stesso ha altresì rappresentato che i condomini
hanno optato per l'applicazione del cd. ''sconto in fattura''.
Ciò premesso, l'Istante chiede quale prezzario deve essere utilizzato per la verifica
della congruità dei prezzi prevista dall'articolo 119, comma 13, del decreto legge n. 34
del 2020.""",
        "circolare",
        "call_Y2n39j40QBFaAK6VzlrYPww4",
    )

    # format_messages(result["messages"])

    # print("=" * 80)
    # print(len(result["list_fonte"]))
    liste = result.update["list_fonte"]
    for fonte in liste:
        print(fonte.id)
        

