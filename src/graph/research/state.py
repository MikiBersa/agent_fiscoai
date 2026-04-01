from typing import Annotated, List, Optional
import operator

from langchain.agents import AgentState
from pydantic import BaseModel, Field


class CitedFonte(BaseModel):
    mongo_id: str
    id: str
    original_text: str
    ricostruito_testo: list[str]
    tipo: str
    score: float
    data: str
    url: str


class Fonte(BaseModel):
    mongo_id: str
    id: str
    original_text: str
    ricostruito_testo: list[str]
    tipo: str
    score: float
    data: str
    url: str
    cites: list[CitedFonte]


class SearchState(AgentState):
    list_fonte: Annotated[list[Fonte], operator.add]
    summary: str
