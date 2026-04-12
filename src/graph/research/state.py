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


def reduce_fonti(left: list[Fonte] | None, right: list[Fonte] | None) -> list[Fonte]:
    if left is None:
        left = []
    if right is None:
        right = []

    # Unisci deduplicando per id
    fonti_dict = {f.id: f for f in left}
    for f in right:
        if f.id in fonti_dict:
            existing_texts = set(fonti_dict[f.id].ricostruito_testo)
            for t in f.ricostruito_testo:
                if t not in existing_texts:
                    fonti_dict[f.id].ricostruito_testo.append(t)
        else:
            fonti_dict[f.id] = f
            
    return list(fonti_dict.values())

def reduce_fonti(left: list[Fonte] | None, right: list[Fonte] | None) -> list[Fonte]:
    return right

class SearchState(AgentState):
    input: str
    list_fonte: Annotated[list[Fonte], reduce_fonti]
    # list_fonte: list[Fonte]
