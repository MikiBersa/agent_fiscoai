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
from src.subagents.calculator.prompts import SYSTEM_PROMPT
from src.subagents.calculator.state import CalcState
from src.subagents.calculator.tools import calculator_python, calculator_wstate
from utils.format import format_messages

model = init_chat_model(
    "azure_openai:gpt-4.1-mini",  # nome modello lato LangChain
    azure_deployment="gpt-4.1-mini",  # oppure il nome reale del deployment Azure
)

tools = [calculator_wstate, calculator_python]  # new tool

# Create agent
calculator_agent = create_agent(
    model,
    tools,
    system_prompt=SYSTEM_PROMPT,
    state_schema=CalcState,  # now defining state scheme
).with_config(
    {"recursion_limit": 20}
)  # recursion_limit limits the number of steps the agent will run


@tool
def calculator_tool(expression: str) -> str:
    """Use the calculator agent to evaluate a mathematical expression."""
    print("=== Calculator agent invoked with expression: ", expression, " ===")
    result = calculator_agent.invoke(
        {"messages": [{"role": "user", "content": expression}]}
    )
    return format_messages(result["messages"])


if __name__ == "__main__":
    # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

    result2 = calculator_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Calcolami integrale del sin(x) tra -1 ed 1",
                }
            ],
        }
    )

    format_messages(result2["messages"])
