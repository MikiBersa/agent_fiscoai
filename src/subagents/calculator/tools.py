import asyncio
import math
from typing import Annotated, List, Literal, Union

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool

# from langchain_sandbox import PyodideSandboxTool
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.types import Command

from src.subagents.calculator.state import CalcState
from utils.format import format_messages


@tool
def calculator_wstate(
    operation: Literal[
        "add",
        "subtract",
        "multiply",
        "divide",
        "sin",
        "cos",
        "radians",
        "exponentiation",
        "sqrt",
    ],
    a: Union[int, float],
    b: Union[int, float],
    state: Annotated[CalcState, InjectedState],  # not sent to LLM
    tool_call_id: Annotated[str, InjectedToolCallId],  # not sent to LLM
) -> Union[int, float]:
    """Define a calculator tool that supports basic arithmetic and trigonometric operations.

    Arg:
        operation (str): The operation to perform ('add', 'subtract', 'multiply', 'divide', 'sin', 'cos', 'radians', 'exponentiation', 'sqrt').
        a (float or int): The first number (or the number to operate on for single-input functions).
        b (float or int, optional): The second number. Defaults to 0. Not used for 'sin', 'cos', 'radians', or 'sqrt'.

    Returns:
        result (float or int): the result of the operation
    Example
        Divide: result   = a / b
        Subtract: result = a - b
        Sine: result = sin(a)
    """

    if operation == "divide" and b == 0:
        return {"error": "Division by zero is not allowed."}

    # Perform calculation
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        result = a / b
    elif operation == "sin":
        result = math.sin(a)
    elif operation == "cos":
        result = math.cos(a)
    elif operation == "radians":
        result = math.radians(a)
    elif operation == "exponentiation":
        result = a**b
    elif operation == "sqrt":
        result = math.sqrt(a)
    else:
        result = "unknown operation"

    # print("PRIMA: ", state["ops"])

    # inserisce operazione fatta
    ops = [f"({operation}, {a}, {b}),"]

    # print("DOPO: ", state["ops"])
    return Command(
        update={
            "ops": ops,
            "messages": [
                # poi per inserire il Tool bisogna salvare id del tool
                ToolMessage(f"{result}", tool_call_id=tool_call_id)
            ],
        }
    )


from daytona import Daytona, DaytonaConfig
from dotenv import load_dotenv
from langchain_daytona import DaytonaSandbox

load_dotenv()
import os

config = DaytonaConfig(api_key=os.getenv("DYTONA_API_KEY"))

# config = DaytonaConfig(api_url="http://localhost:3000/api", api_key="secret_api_token")


sandbox = Daytona(config).create()
backend = DaytonaSandbox(sandbox=sandbox)

model = init_chat_model(
    "azure_openai:gpt-4.1-mini",  # nome modello lato LangChain
    azure_deployment="gpt-4.1-mini",  # oppure il nome reale del deployment Azure
)


# Create an agent with the sandbox tool
agent = create_deep_agent(
    model=model,
    system_prompt="You are a Python coding assistant with sandbox access.",
    backend=backend,
)


@tool
def calculator_python(
    query: str,
    state: Annotated[CalcState, InjectedState],  # not sent to LLM
    tool_call_id: Annotated[str, InjectedToolCallId],  # not sent to LLM
) -> Union[int, float]:
    """Solve mathematical or logical problems by generating and executing Python code.

    This tool takes a natural language description of a problem, translates it into
    executable Python code, and returns the result from a secure sandbox. Use this
    for any calculation that is too complex for basic operators, including
    trigonometry, advanced math, or multi-step algorithmic problems.

    Args:
        query (str): A natural language description of the calculation or logic to perform.
                    Examples: 'Calculate 35% of 150', 'How many minutes in 3 days?',
                    'Solve the quadratic equation x^2 - 4x + 4 = 0'.

    Returns:
        The result of the computation.
    """

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    ops = [f"({query})"]

    text = format_messages(result["messages"])
    # print("TEXT: ", text)

    return Command(
        update={
            "ops": ops,
            "messages": [
                # poi per inserire il Tool bisogna salvare id del tool
                ToolMessage(f"{text}", tool_call_id=tool_call_id)
            ],
        }
    )
