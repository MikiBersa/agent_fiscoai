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

from bson import ObjectId

from src.graph.research.state import CitedFonte, Fonte
from src.services.mongodb import MongoDBConnection


def build_chunk_window(
    num_chunk: int, max_chunk: int, window_size: int = 5
) -> list[int]:
    """
    Restituisce una finestra di chunk centrata su num_chunk, quando possibile.

    Esempi con window_size=5:
    - centro ideale: [num_chunk-2, num_chunk-1, num_chunk, num_chunk+1, num_chunk+2]
    - se num_chunk è vicino all'inizio, prende più chunk a destra
    - se num_chunk è vicino alla fine, prende più chunk a sinistra

    Args:
        num_chunk: chunk corrente
        max_chunk: indice massimo disponibile
        window_size: numero totale di chunk da restituire

    Returns:
        Lista ordinata di indici chunk validi
    """
    if window_size <= 0:
        return []

    if num_chunk < 0 or num_chunk > max_chunk:
        raise ValueError(f"num_chunk ({num_chunk}) deve essere tra 0 e {max_chunk}")

    half = window_size // 2

    start = num_chunk - half
    end = num_chunk + half

    # Se vai sotto 0, sposti tutto a destra
    if start < 0:
        end += -start
        start = 0

    # Se vai oltre max_chunk, sposti tutto a sinistra
    if end > max_chunk:
        shift = end - max_chunk
        start -= shift
        end = max_chunk

        if start < 0:
            start = 0

    return list(range(start, end + 1))


def estrazione_circolari(result):
    fonte = {
        "mongo_id": "",
        "id": "",
        "original_text": "",
        "ricostruito_testo": "",
        "tipo": "circolare",
        "score": 0.0,
        "data": "",
        "cites": [],
    }

    mongodb = MongoDBConnection()
    mongodb.connection()
    mongodb.set_collection("circolari_chunk")

    id = result["id"]

    circolare_chunk = mongodb.get_circolare_chunk(
        filtro={"_id": ObjectId(id)},
        procet={"parent_id": 1, "text": 1, "num_chunk": 1, "id": 1},
    )

    nome_id = circolare_chunk["id"]

    # 1) ritorno del padre

    mongodb.set_collection("circolari_original")
    circolare_original = mongodb.get_circolare_chunk(
        filtro={"_id": circolare_chunk["parent_id"]},
        procet={"info": 1, "id": 1, "url": 1},
    )

    if circolare_original is None:
        mongodb.set_collection("circolari")
        circolare_original = mongodb.get_circolare_chunk(
            filtro={"_id": circolare_chunk["parent_id"]},
            procet={"info": 1, "id": 1, "url": 1},
        )

    print(circolare_original)

    fonte["mongo_id"] = str(circolare_original["_id"])
    fonte["id"] = str(circolare_original["id"])
    fonte["data"] = str(circolare_original["info"]["data"])
    fonte["original_text"] = "\n\n".join(circolare_original["info"]["pagine"])

    mongodb.set_collection("circolari_chunk")

    id = result["id"]

    circolare_chunks = mongodb.get_circolare_chunks(
        filtro={"id": nome_id},
        procet={"id": 1},
    )

    num_total = len(circolare_chunks)

    array_chunk = 

    if circolare_chunk["num_chunk"] == 0:
        id = result["id"]
        array_chunk = [0, 1, 2, 3, 4]
        circolare_chunks = mongodb.get_circolare_chunks(
            filtro={"_id": ObjectId(id), "num_chunk": {"$in": array_chunk}},
            procet={"text": 1},
        )
    else:
        array_chunk = [0, 1, circolare_chunk["num_chunk"], 3, 4]

    """
    2) espansione a paragrafo
    3) espansione citazioni
    5) controllare doppioni dopo
    """

    #  4) costruzione dell'oggetto
    fonte = Fonte(
        mongo_id=fonte["mongo_id"],
        id=fonte["id"],
        original_text=fonte["original_text"],
        tipo=fonte["tipo"],
        score=0.0,
        data=fonte["data"],
        cites=[],
    )
    return fonte


if __name__ == "__main__":
    print(estrazione_circolari({"id": "67f12a3172d91a31f1960862"}))
