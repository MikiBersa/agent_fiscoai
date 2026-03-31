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

from IPython.display import Image, display
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from src.graph.research.tools import rag_query

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
    state_schema=DeepAgentState,  # now defining state scheme
).with_config({"recursion_limit": 5})
