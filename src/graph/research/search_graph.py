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

from datetime import datetime

from IPython.display import Image, display
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from src.graph.research.prompts import RESEARCHER_INSTRUCTIONS
from src.graph.research.state import SearchState
from src.graph.research.tools import rag_query
from utils.format import format_messages


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")


model = init_chat_model(
    "azure_openai:gpt-4.1-mini",  # nome modello lato LangChain
    azure_deployment="gpt-4.1-mini",  # oppure il nome reale del deployment Azure
)

tools = [rag_query]  # new tool

# Create agent
web_search_agent = create_agent(
    model,
    tools,
    system_prompt=RESEARCHER_INSTRUCTIONS.format(date=get_today_str()),
    state_schema=SearchState,  # now defining state scheme
).with_config({"recursion_limit": 10})


if __name__ == "__main__":
    # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

    result = web_search_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Come devono essere rilevati in bilancio d’esercizio, secondo i principi OIC, i ricavi da affitti non fatturati successivamente all’attivazione di una composizione negoziata per crisi d’impresa?",
                }
            ],
            "list_fonte": [],
        }
    )

    format_messages(result["messages"])

    print("=" * 80)
    print(len(result["list_fonte"]))
