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

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from typing_extensions import Literal

from src.graph.scope.prompts import (
    clarify_with_user_instructions,
    transform_messages_into_research_topic_prompt,
)
from src.graph.scope.state import (
    AgentInputState,
    AgentState,
    ClarifyWithUser,
    ResearchQuestion,
)
from utils.format import format_messages

# ===== UTILITY FUNCTIONS =====


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")


model = init_chat_model(
    "azure_openai:gpt-4.1-mini",  # nome modello lato LangChain
    azure_deployment="gpt-4.1-mini",  # oppure il nome reale del deployment Azure
)

# ===== WORKFLOW NODES =====


def clarify_with_user(
    state: AgentState,
) -> Command[Literal["write_research_brief", "__end__"]]:
    """
    Determine if the user's request contains sufficient information to proceed with research.

    Uses structured output to make deterministic decisions and avoid hallucination.
    Routes to either research brief generation or ends with a clarification question.
    """
    # Set up structured output model
    structured_output_model = model.with_structured_output(ClarifyWithUser)

    # Invoke the model with clarification instructions
    response = structured_output_model.invoke(
        [
            HumanMessage(
                content=clarify_with_user_instructions.format(
                    messages=get_buffer_string(messages=state["messages"]),
                    date=get_today_str(),
                )
            )
        ]
    )

    # Route based on clarification need
    if response.need_clarification:
        return Command(
            goto=END, update={"messages": [AIMessage(content=response.question)]}
        )
    else:
        return Command(
            goto="write_research_brief",
            update={"messages": [AIMessage(content=response.verification)]},
        )


def write_research_brief(state: AgentState):
    """
    Transform the conversation history into a comprehensive research brief.

    Uses structured output to ensure the brief follows the required format
    and contains all necessary details for effective research.
    """
    # Set up structured output model
    structured_output_model = model.with_structured_output(ResearchQuestion)

    # Generate research brief from conversation history
    response = structured_output_model.invoke(
        [
            HumanMessage(
                content=transform_messages_into_research_topic_prompt.format(
                    messages=get_buffer_string(state.get("messages", [])),
                    date=get_today_str(),
                )
            )
        ]
    )

    # Update state with generated research brief and pass it to the supervisor
    return {
        "research_brief": response.research_brief,
        "supervisor_messages": [HumanMessage(content=f"{response.research_brief}.")],
    }


# ===== GRAPH CONSTRUCTION =====

# Build the scoping workflow
deep_researcher_builder = StateGraph(AgentState, input_schema=AgentInputState)

# Add workflow nodes
deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
deep_researcher_builder.add_node("write_research_brief", write_research_brief)

# Add workflow edges
deep_researcher_builder.add_edge(START, "clarify_with_user")
deep_researcher_builder.add_edge("write_research_brief", END)

# Compile the workflow
checkpointer = InMemorySaver()
scope_research = deep_researcher_builder.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    # display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

    from langchain_core.messages import HumanMessage

    thread = {"configurable": {"thread_id": "2"}}
    result = scope_research.invoke(
        {
            "messages": [
                HumanMessage(
                    content="I want to research the best coffee shops in San Francisco."
                )
            ]
        },
        config=thread,
    )
    format_messages(result["messages"])
