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

def estrazione_circolari(result):
    mongodb = MongoDBConnection()
    mongodb.connection()
    mongodb.set_collection("circolari_chunk")

    id = result["id"]

    circolare_chunk = mongodb.get_circolare_chunk(filtro={"_id": ObjectId(id)}, procet={"parent_id": 1, "text-embedding-3-large-1024": 0, "text-embedding-3-large": 0})

    return circolare_chunk

if __name__ == "__main__":
    print(estrazione_circolari({"id": '67f12a3172d91a31f1960862'}))