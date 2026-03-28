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
from langchain_core.tools import tool

# Create agent using create_react_agent directly
from src.subagents.websearch.prompts import RESEARCHER_INSTRUCTIONS
from src.subagents.websearch.state import DeepAgentState
from src.subagents.websearch.tools import tavily_search, think_tool, get_today_str
from utils.format import format_messages

model = init_chat_model(
    "azure_openai:gpt-4.1-mini",  # nome modello lato LangChain
    azure_deployment="gpt-4.1-mini",  # oppure il nome reale del deployment Azure
)

tools = [tavily_search, think_tool]  # new tool

# Create agent
agent = create_agent(
    model,
    tools,
    system_prompt=RESEARCHER_INSTRUCTIONS.format(date=get_today_str()),
    state_schema=DeepAgentState,  # now defining state scheme
).with_config(
    {"recursion_limit": 20}
)  # recursion_limit limits the number of steps the agent will run

if __name__ == "__main__":
    # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

    result2 = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Qual è il papa attuale di oggi?",
                }
            ],
        }
    )

    format_messages(result2["messages"])
