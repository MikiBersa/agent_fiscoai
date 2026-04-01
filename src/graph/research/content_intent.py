from dotenv import load_dotenv

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field

class CitazioneFonte(BaseModel):
    check_presenza: bool = Field(description="Verifica se è presente nel teso una citazione ad una legge della normativa, se sì metti true e no False")
    anno_norma: str = Field(description="Anno della normativa citata")
    numero_norma: str = Field(description="Numero della normativa citata")
    articolo_norma: str = Field(description="Verifica se è presente il numero dell'articolo nella citazione se non è presete ritorna '', se è presente ritorna il numero dell'articolo")
    

content_intent_prompt = ChatPromptTemplate.from_template(
    """Analizza il testo fornito e determina se contiene citazioni a leggi o normative. 

    Per esempio:
    articolo 119 comma 13 decreto legge 34 2020

    rilascia in output:
    check_presenza: true
    anno_norma: 2020
    numero_norma: 34
    articolo_norma: 119

    NON Mettere il numero dei commi in articolo_norma, metti solo il numero dell'articolo.

    Il testo da analizzare è il seguente:
    {text}

    Se sì, estrai le seguenti informazioni:
    - Anno della normativa
    - Numero della normativa
    - Articolo della normativa
    Se no, ritorna '' per tutte le informazioni.
    """
)


content_intent = content_intent_prompt | AzureChatOpenAI(
    azure_deployment="gpt-4.1-mini",
    api_version="2024-12-01-preview",
).with_structured_output(CitazioneFonte)