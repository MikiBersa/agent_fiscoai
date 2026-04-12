from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

def rewrting_query(
    input: str,
    query: str,
) -> str:
    """Questo tool fa un riassunto dettagliato delle informazioni trovate durate la richerca.

    Args:

    Returns:
        I risultati della ricerca formattati come testo leggibile.
    """

    print("==== rewrting_query ====")

    
    rewrite_prompt = ChatPromptTemplate.from_template(
        """
        Sei un eseperto elaboratore di tesi italiani in ambito fiscale e conosci come scrivere query per ottimizzaree
        la ricerca nei rag hybrid quindi dense vector search + keywords bm25.

        Il tuo scopo è riscrivere la query in modo che sia più efficace per la ricerca.
        Prendi in considerazione input dell'utente e lo scopo di ricerca: devi ritornare in output una query che massimizzi la ricerca RAG ma che metta assieme i concetti dell'input e 
        query così da fare ricerche sempre riferite all'input ma con aggiunga dell'informazione specifica da cercare, qiundi riscrivi input in modo tale che possa permettere
        di cercare le informazioni richieste in query.

        Input: {input}
        Query: {query}
        
        Output: 
        """
    )

    rewrite_agent = rewrite_prompt | AzureChatOpenAI(
        azure_deployment="gpt-4.1-mini",
        api_version="2024-12-01-preview",
        max_tokens=1000,
    )

    summary = rewrite_agent.invoke({"input": input, "query": query})

    return summary.content