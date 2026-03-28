import os
import sys
import warnings

# Suppress Pydantic V1 migration warnings in Python 3.14+
warnings.filterwarnings("ignore", category=UserWarning, message=".*Pydantic V1 functionality.*")

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from dotenv import load_dotenv

load_dotenv()

from IPython.display import Image, display
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain.agents import create_agent

# Create agent using create_react_agent directly
from src.subagents.calculator.prompts import SYSTEM_PROMPT
from src.subagents.calculator.tools import calculator_wstate, calculator_python
from src.subagents.calculator.state import CalcState
from utils.format import format_messages

model = init_chat_model(
    "azure_openai:gpt-5-mini",  # nome modello lato LangChain
    azure_deployment="gpt-5-mini",  # oppure il nome reale del deployment Azure
)

tools = [calculator_wstate, calculator_python]  # new tool

# Create agent
agent = create_agent(
    model,
    tools,
    system_prompt=SYSTEM_PROMPT,
    state_schema=CalcState,  # now defining state scheme
).with_config({"recursion_limit": 20})  #recursion_limit limits the number of steps the agent will run

if __name__ == "__main__":
    # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

    result2 = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Calcola la somma di tutti i numeri da 1 a 1.000.000 che sono multipli di 3 oppure di 5, ma non di entrambi.",
                }
            ],
        }
    )

    format_messages(result2["messages"])
    