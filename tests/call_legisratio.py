import sys
import os
import requests
import json

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.mongodb import MongoDBConnection
from src.services.qdrant import QdrantHybridRetriever
from src.services.embeddings import EmbeddingAzure

# Constants
LEGISRATIO_URL = "https://api.legisratio.com/graphql"
LEGISRATIO_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1ZDZmNzlkYS05ZmUwLTQ2ZTgtYmJjZi1mYTk3YWZlMjU1MmMiLCJjbGllbnRfaWQiOiI1ZDZmNzlkYS05ZmUwLTQ2ZTgtYmJjZi1mYTk3YWZlMjU1MmMiLCJzY29wZSI6ImdyYXBocWw6cmVhZCIsImlhdCI6MTc3NjE0NzY4MiwiaXNzIjoiaHR0cHM6Ly9hcGkubGVnaXNyYXRpby5jb20ifQ.QjISiK_W52De1QWQbcewdeoWiKklKDNXWYQAPV-YIGc"


def call_legisratio(query_text):
    """
    Calls the Legisratio GraphQL API for hybrid search.
    """
    headers = {
        "Authorization": f"Bearer {LEGISRATIO_TOKEN}",
        "Content-Type": "application/json"
    }
    
    graphql_query = """
    query HybridSearch($searchString: String!, $k: Int, $levels: [Level], $effort: String) {
      HybridSearch(searchString: $searchString, k: $k, levels: $levels, effort: $effort) {
        LawID
        LawTitle
        Link
        ArticleID
        ArticleNumber
        ArticleTitle
        ArticleText
        ArticleTopics
        PublicationDate
        TypeLaw
        rankValue
        CentralityScore
      }
    }
    """
    
    variables = {
        "searchString": query_text,
        "k": 20,
        "effort": "high"
    }
    
    try:
        response = requests.post(
            LEGISRATIO_URL,
            json={"query": graphql_query, "variables": variables},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error calling Legisratio: {e}")
        return None

def main():

    dati_ = []
    # 1. Setup MongoDB connection
    # azure=True uses the MONGODB_CONNECTION = "mongodb://100.77.246.20:27017/"
    mongo = MongoDBConnection(
        collection_name="fiscoggi",
        db_name="vertical_ai",
        azure=True
    )
    mongo.connection()
    
    # Filter: question exists and is not empty, and references is not empty
    # Assuming references is a list/array
    filtro = {
        "question": {"$exists": True, "$ne": ""},
        "references": {"$exists": True, "$not": {"$size": 0}}
    }
    
    # Projection requirements
    projection = {"question": 1, "references_llm": 1, "_id": 1}
    
    print("Fetching test data from MongoDB (db: vertical_ai, collection: fiscoggi)...")
    docs = mongo.get_chunks(filtro=filtro, procet=projection)
    
    # 2. Setup Qdrant Retriever
    azure_embedding = EmbeddingAzure()
    qdrant_url = "http://100.77.246.20:6333"
    retriever = QdrantHybridRetriever(
        qdrant_url=qdrant_url,
        provider_embedding=azure_embedding
    )
    
    # 3. Iterate through test cases
    count = 0
    for doc in docs:
        print("conto: ", count)
        count += 1
        question = doc.get("question")
        ref_llm = doc.get("references_llm")

        if ref_llm.get("reference_law") == []:
            continue

        elem_dato = {
            "id": str(doc["_id"]),
            "question": question,
            "expected_refs": ref_llm.get("reference_law"),
            "qdrant_results": [],
            "legisratio_results": []
        }

        
        qdrant_results = []
        legisratio_results = []
        # --- CALL LEGISRATIO ---
        print("[LEGISRATIO] Running query...")
        legis_res = call_legisratio(question)
        if legis_res and "data" in legis_res:
            results = legis_res["data"].get("HybridSearch", [])
            # print(f"[LEGISRATIO] Found {len(results)} results.")
            for i, r in enumerate(results): # Show top 5
                # print(f"  {i+1}. {r.get('LawTitle')} - Art. {r.get('ArticleNumber')} (Score: {r.get('rankValue')})")
                
                legisratio_results.append({
                    "nome_id": r.get("ArticleID"),
                    "score": r.get("rankValue"),
                })
        else:
            print("[LEGISRATIO] No results or error.")
        
            
        # --- CALL QDRANT ---
        print("\n[QDRANT] Running hybrid search...")
        try:
            build_filter = retriever.build_filter(
                tipo="norma"
            )
            qdrant_res = retriever.search(question, mode="hybrid", limit=20, query_filter=build_filter)
            formatted = retriever.format_results(qdrant_res)
            # print(f"[QDRANT] Found {len(formatted)} results.")
            for i, f in enumerate(formatted): # Show top 5
                nome_ids = f['name_id'].split("_")
                
                if len(nome_ids) == 3:
                    numero_ = nome_ids[0]
                    numero = ""
                    for num in numero_:
                        if num.isdigit():
                            numero += num
                    
                    articolo = nome_ids[1].replace("A", "").replace("0","")
                    anno = nome_ids[2].split("-")[-1]
                    nome_id = anno+"|"+numero+"#"+articolo
                else:
                    numero_ = nome_ids[0]
                    numero = ""
                    for num in numero_:
                        if num.isdigit():
                            numero += num
                    anno = nome_ids[1].split("-")[-1]
                    articolo = ""
                    nome_id = anno+"|"+numero
                
                qdrant_results.append({
                    "original_name": f['name_id'],
                    "nome_id": nome_id,
                    "score": f['score'],
                })
        except Exception as e:
            print(f"[QDRANT] Error: {e}")

        elem_dato["qdrant_results"] = qdrant_results
        elem_dato["legisratio_results"] = legisratio_results
        dati_.append(elem_dato)

        with open("tests/test_results.json", "w", encoding="utf-8") as f:
            json.dump(dati_, f, ensure_ascii=False, indent=4)

        print("SALVATO")

if __name__ == "__main__":
    main()