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

    circolare_chunk = mongodb.get_chunk(
        filtro={"_id": ObjectId(id)},
        procet={"parent_id": 1, "text": 1, "num_chunk": 1, "id": 1},
    )

    nome_id = circolare_chunk["id"]

    # 1) ritorno del padre

    mongodb.set_collection("circolari_original")
    circolare_original = mongodb.get_chunk(
        filtro={"_id": circolare_chunk["parent_id"]},
        procet={"info": 1, "id": 1, "url": 1},
    )

    if circolare_original is None:
        mongodb.set_collection("circolari")
        circolare_original = mongodb.get_chunk(
            filtro={"_id": circolare_chunk["parent_id"]},
            procet={"info": 1, "id": 1, "url": 1},
        )

    # print(circolare_original)

    fonte["mongo_id"] = str(circolare_original["_id"])
    fonte["id"] = str(circolare_original["id"])
    fonte["data"] = str(circolare_original["info"]["data"])
    fonte["original_text"] = "\n\n".join(circolare_original["info"]["pagine"])
    fonte["url"] = str(circolare_original["url"])

    # print("=====")

    # 2) espansione a paragrafo
    mongodb.set_collection("circolari_chunk")

    num_total = mongodb.count_chunks(filtro={"id": nome_id})

    print("NOME ID: ", nome_id, num_total)

    # print("=====: ", num_total)

    array_chunk = build_chunk_window(circolare_chunk["num_chunk"], num_total)

    print(array_chunk)

    circolare_chunks = mongodb.get_chunks(
        filtro={"id": nome_id, "num_chunk": {"$in": array_chunk}},
        procet={"text": 1},
    )

    """
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
        ricostruito_testo=[elem["text"] for elem in circolare_chunks],
        url=fonte["url"],
        cites=[],
    )
    return fonte


def estrazione_giurisprudenza(result):
    fonte = {
        "mongo_id": "",
        "id": "",
        "original_text": "",
        "ricostruito_testo": "",
        "tipo": "giurisprudenza",
        "score": 0.0,
        "data": "",
        "cites": [],
    }

    mongodb = MongoDBConnection()
    mongodb.connection()
    mongodb.set_collection("giurisprudenza_chunk")

    id = result["id"]

    giurisprudenza_chunk = mongodb.get_chunk(
        filtro={"_id": ObjectId(id)},
        procet={"parent_id": 1, "text": 1, "chunk_number": 1, "nome_id": 1},
    )

    nome_id = giurisprudenza_chunk["nome_id"]

    # 1) ritorno del padre

    mongodb.set_collection("giurisprudenza_original")
    giurisprudenza_original = mongodb.get_chunk(
        filtro={"_id": str(giurisprudenza_chunk["parent_id"])},
        procet={"testo": 1, "nome_id": 1, "url": 1, "data": 1},
    )

    # print(circolare_original)

    fonte["mongo_id"] = str(giurisprudenza_original["_id"])
    fonte["id"] = str(giurisprudenza_original["nome_id"])
    fonte["data"] = str(giurisprudenza_original["data"])
    fonte["original_text"] = giurisprudenza_original["testo"]
    fonte["url"] = str(giurisprudenza_original["url"])

    # print("=====")

    # 2) espansione a paragrafo
    mongodb.set_collection("giurisprudenza_chunk")

    num_total = mongodb.count_chunks(filtro={"nome_id": nome_id})

    print("NOME ID: ", nome_id, num_total)

    # print("=====: ", num_total)

    array_chunk = build_chunk_window(giurisprudenza_chunk["chunk_number"], num_total)

    print(array_chunk)

    giurisprudenza_chunks = mongodb.get_chunks(
        filtro={"nome_id": nome_id, "chunk_number": {"$in": array_chunk}},
        procet={"text": 1},
    )

    """
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
        ricostruito_testo=[elem["text"] for elem in giurisprudenza_chunks],
        url=fonte["url"],
        cites=[],
    )
    return fonte

def estrazione_risoluzione(result):
    fonte = {
        "mongo_id": "",
        "id": "",
        "original_text": "",
        "ricostruito_testo": "",
        "tipo": "risoluzione",
        "score": 0.0,
        "data": "",
        "cites": [],
    }

    mongodb = MongoDBConnection()
    mongodb.connection()
    mongodb.set_collection("risoluzioni_chunk")

    id = result["id"]

    risoluzione_chunk = mongodb.get_chunk(
        filtro={"_id": ObjectId(id)},
        procet={"parent_id": 1, "text": 1, "num_chunk": 1, "id": 1},
    )

    nome_id = risoluzione_chunk["id"]

    # 1) ritorno del padre

    mongodb.set_collection("risoluzioni_original")
    risoluzione_original = mongodb.get_chunk(
        filtro={"_id": risoluzione_chunk["parent_id"]},
        procet={"info": 1, "id": 1, "url": 1},
    )

    # print(circolare_original)

    fonte["mongo_id"] = str(risoluzione_original["_id"])
    fonte["id"] = str(risoluzione_original["id"])
    fonte["data"] = str(risoluzione_original["info"]["data"])
    fonte["original_text"] = "\n\n".join(risoluzione_original["info"]["pagine"])
    fonte["url"] = str(risoluzione_original["url"])

    # print("=====")

    # 2) espansione a paragrafo
    mongodb.set_collection("risoluzioni_chunk")

    num_total = mongodb.count_chunks(filtro={"id": nome_id})

    print("NOME ID: ", nome_id, num_total)

    # print("=====: ", num_total)

    array_chunk = build_chunk_window(risoluzione_chunk["num_chunk"], num_total)

    print(array_chunk)

    risoluzione_chunks = mongodb.get_chunks(
        filtro={"id": nome_id, "num_chunk": {"$in": array_chunk}},
        procet={"text": 1},
    )

    """
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
        ricostruito_testo=[elem["text"] for elem in risoluzione_chunks],
        url=fonte["url"],
        cites=[],
    )
    return fonte


if __name__ == "__main__":
    print("CIRCOLARE")
    elem: Fonte = estrazione_circolari({"id": "67f12a3172d91a31f1960862"})

    for elem_ in elem.ricostruito_testo:
        print(elem_[:30])
        print("=" * 80)

    print("GIURI")
    elem: Fonte = estrazione_giurisprudenza({"id": "6887f9562b2786535ee7a6aa"})

    for elem_ in elem.ricostruito_testo:
        print(elem_[:30])
        print("=" * 80)

    print("RISOLUZIONI")
    elem: Fonte = estrazione_risoluzione({"id": "67f44fd5dd2da090401d31c4"})

    for elem_ in elem.ricostruito_testo:
        print(elem_[:30])
        print("=" * 80)
