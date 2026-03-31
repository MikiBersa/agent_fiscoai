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

from src.services.mongodb import MongoDBConnection
from bson import ObjectId
from src.graph.research.state import Fonte, CitedFonte

def estrazione_circolari(result):
    mongodb = MongoDBConnection()
    mongodb.connection()
    mongodb.set_collection("circolari_chunk")

    id = result["id"]

    circolare_chunk = mongodb.get_circolare_chunk(filtro={"_id": ObjectId(id)}, procet={"parent_id": 1})

    """
    1) ritorno del padre
    2) espansione a paragraf0
    3) espansione citazioni
    4) costruzione dell'oggetto
    """
    return circolare_chunk

if __name__ == "__main__":
    print(estrazione_circolari({"id": '67f12a3172d91a31f1960862'}))