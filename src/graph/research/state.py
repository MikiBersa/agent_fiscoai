from typing import List, Optional

from langchain.agents import AgentState
from pydantic import BaseModel, Field


class Fonte(BaseModel):
    mongo_id: str
    id: str
    original_text: str
    ricostruito_testo: list[str]
    tipo: str
    score: float
    data: str


class SearchState(AgentState):
    list_fonte: list[Fonte]
