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

from datetime import datetime

from IPython.display import Image, display
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from src.graph.research.prompts import RESEARCHER_INSTRUCTIONS
from src.graph.research.state import SearchState
from src.graph.research.tools import rag_query, rag_query_norma_specifica
from utils.format import format_messages


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")


model = init_chat_model(
    "openai:gpt-4.1-mini",  # nome modello lato LangChain
    # model="gpt-4.1-mini",  # oppure il nome reale del deployment Azure
)

# TODO CONTROLALRE CHE 
tools = [rag_query, rag_query_norma_specifica]  # new tool

# TODO RENDERLO PIù DETEMINISTICO
# Create agent
rag_search_agent = create_agent(
    model,
    tools,
    system_prompt=RESEARCHER_INSTRUCTIONS.format(date=get_today_str()),
    state_schema=SearchState,  # now defining state scheme
)
# .with_config({"recursion_limit": 20})

if __name__ == "__main__":
    # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

    result = rag_search_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": """L'Istante, condomino di un ''condominio minimo'' situato nel territorio della
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
                }
            ],
            "list_fonte": [],
        }
    )

    format_messages(result["messages"])

    print("=" * 80)
    print(len(result["list_fonte"]))
