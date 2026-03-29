import os
import sys
import warnings

# Suppress Pydantic V1 migration warnings in Python 3.14+
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Pydantic V1 functionality.*"
)

# Add the project root to sys.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from src.subagents.websearch.state import DeepAgentState
from src.subagents.prompts import INSTRUCTIONS

from src.subagents.calculator.calculator import calculator_tool
from src.subagents.todo.todo_agent import todo_tool
from src.subagents.websearch.web_search import web_search_tool
from langchain.agents import create_agent
from utils.format import format_messages


model = init_chat_model(
    "azure_openai:gpt-4.1-mini",  # nome modello lato LangChain
    azure_deployment="gpt-4.1-mini",  # oppure il nome reale del deployment Azure
)

tools = [calculator_tool, todo_tool, web_search_tool]

supervisor_agent = create_agent(
    model,
    tools,
    system_prompt=INSTRUCTIONS,
    state_schema=DeepAgentState,  # now defining state scheme
).with_config(
    {"recursion_limit": 20}
)  # recursion_limit limits the number of steps the agent will run


if __name__ == "__main__":
    # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

    result2 = supervisor_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "un'azienda ha dato in affitto a un cliente un capannone , nel corso dell'anno il cliente è entrato in composizione negoziata per crisi d'impresa. Gli affitti non fatturati dal momento di attivazione della crisi vanno rilevati in bilancio?",
                }
            ],
        }
    )

    format_messages(result2["messages"])
