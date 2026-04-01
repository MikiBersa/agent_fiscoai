import os
import sys
import warnings

# Suppress Pydantic warnings
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Pydantic V1 functionality.*"
)
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Pydantic serializer warnings:.*"
)
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*PydanticSerializationUnexpectedValue.*"
)

# Add the project root to sys.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from dotenv import load_dotenv

load_dotenv()

import operator
from typing import Annotated, List, Literal, Tuple, Union

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from src.graph.think.search_support import search_agent
from src.graph.think.thinker import thinker
from utils.format import format_messages
from src.graph.think.response import response_llm
from src.graph.research.search_graph import rag_search_agent


class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    thinker: str


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )


class Response(BaseModel):
    """Response to user."""

    response: str


class Act(BaseModel):
    """Action to perform."""

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )


planner_prompt = ChatPromptTemplate.from_template(
"""
You are a planning agent.

Your task is to generate a clear, minimal, and effective step-by-step plan to solve the user's objective.

You MUST base your planning on the strategic analysis provided by the THINKER.

---------------------
THINKER ANALYSIS
---------------------
{thinker}   
---------------------

Instructions:

1. Carefully read and incorporate the THINKER analysis:
   - Use the identified sub-problems
   - Focus on gaps, weaknesses, and areas to deepen
   - Prioritize critical points highlighted by the THINKER

2. Generate a step-by-step plan:
   - Each step must be necessary and non-redundant
   - Each step must be actionable and clearly defined
   - Do NOT skip reasoning steps if they are required
   - Do NOT include irrelevant or superficial steps

3. The plan must:
   - Address all key sub-problems
   - Include steps to fill identified knowledge gaps
   - Include steps for deeper analysis where required
   - Lead deterministically to the final answer

4. The final step MUST produce the final answer.

5. Each step must contain all required information to be executed independently.

Output format:
- Numbered list of steps
- No explanations outside the steps
- Keep it concise but complete

Messages:
{messages}
"""
)

planner = planner_prompt | AzureChatOpenAI(
    azure_deployment="gpt-4.1-mini",
    api_version="2024-12-01-preview",
).with_structured_output(Plan)


replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
    This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
    The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

    Your objective was this:
    {input}

    Your original plan was this:
    {plan}

    You have currently done the follow steps:
    {past_steps}

    Think about:
    {thinker}

    Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
)


replanner = replanner_prompt | AzureChatOpenAI(
    azure_deployment="gpt-4.1-mini",
    api_version="2024-12-01-preview",
).with_structured_output(Act)


# COSTRUZIONE DEL GRAFO

# AGENTE SEMPLICE


async def execute_step(state: PlanExecute):
    plan = state["plan"]

    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    task = plan[0]

    task_formatted = f"""For the following plan:
    {plan_str}\n\nYou are tasked with executing step {1}, {task}."""

    #agent_response = await search_agent.ainvoke(
    #    {"messages": [("user", task_formatted)]}
    #)

    agent_response = await rag_search_agent.ainvoke(
        {"messages": [{"role": "user", "content": task_formatted}], "list_fonte": [],}
    )

    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
    }


async def plan_step(state: PlanExecute):
    plan = await planner.ainvoke({
        "messages": [("user", state["input"])],
        "thinker": state.get("thinker", "")
    })
    return {"plan": plan.steps}


async def replan_step(state: PlanExecute):
    # QUI METTERE UN LIMITE NEL REPLANNING

    output = await replanner.ainvoke(state)

    if isinstance(output.action, Response):
        return {"response": output.action.response}
    else:
        # TODO IN QUESTO CASO FORZARLO A DARE UNA RISPOSTA
        if len(state["past_steps"]) > 5:
            output = await response_llm.ainvoke(state)
            return {"response": output.content}
        return {"plan": output.action.steps}


def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"


async def thinker_step(state: PlanExecute):
    thinker_response = await thinker.ainvoke({"messages": [("user", state["input"])]})
    return {"thinker": thinker_response.content}


workflow = StateGraph(PlanExecute)

workflow.add_node("pre_thinker", thinker_step)
workflow.add_node("post_thinker", thinker_step)

# Add the plan node
workflow.add_node("planner", plan_step)

# Add the execution step
workflow.add_node("agent", execute_step)

# Add a replan node
workflow.add_node("replan", replan_step)

# STRUTTURA DEL GRAFO
workflow.add_edge(START, "pre_thinker")

workflow.add_edge("pre_thinker", "planner")

# From plan we go to agent
workflow.add_edge("planner", "agent")

workflow.add_edge("agent", "post_thinker")

# From agent, we replan
workflow.add_edge("post_thinker", "replan")

workflow.add_conditional_edges(
    "replan",
    # Next, we pass in the function that will determine which node is called next.
    should_end,
    ["agent", END],
)

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
todo_workflow = workflow.compile()

if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage
    from IPython.display import Image, display

    # display(Image(todo_workflow.get_graph(xray=True).draw_mermaid_png()))

    async def main():
        thread = {"configurable": {"thread_id": "2"}}
        inputs = {"input": """L'Istante, condomino di un ''condominio minimo'' situato nel territorio della
Regione X composto da n. 5 unità immobiliari, unitamente agli altri proprietari
e comodatari, ha deliberato e incaricato una ditta edile di effettuare interventi di
efficientamento energetico di cui all'articolo 119 del decreto legge n. 34 del 2020 (cd.
Superbonus), con conseguente presentazione della CILAS in data 15 aprile 2022.
L'Istante rappresenta che intende sostituire (come intervento ''trainato'') le
finestre e persiane ''ad arco'' dell'intero edificio con il mantenimento della stessa forma e
che, al momento della firma del contratto di appalto avvenuto ad aprile 2022, il prezzario
Pagina 2 di 5
della Regione X non contemplava tale tipologia di infisso e, pertanto, è stato utilizzato
il prezzario della ''vicina'' Regione Y edizione 2021 che, invece, la prevedeva.
L'Istante fa presente che la sostituzione delle finestre e persiane è attualmente in
corso e che, nel frattempo, la Regione X ha aggiornato il prezzario includendovi anche
i prezzi riferiti alla sostituzione delle persiane e delle finestre ''ad arco''.
Con documentazione integrativa l'Istante ha specificato che per l'intervento
complessivo prospettato è stato completato il primo SAL, in data 2 maggio 2023, e che
il secondo e ultimo SAL, nel quale confluirà anche l'intervento trainato di sostituzione
delle finestre e persiane, è in corso. Lo stesso ha altresì rappresentato che i condomini
hanno optato per l'applicazione del cd. ''sconto in fattura''.
Ciò premesso, l'Istante chiede quale prezzario deve essere utilizzato per la verifica
della congruità dei prezzi prevista dall'articolo 119, comma 13, del decreto legge n. 34
del 2020."""}

        async for event in todo_workflow.astream(inputs, config=thread):
            for k, v in event.items():
                if k != "__end__":
                    print(v)
                    print("="*80)

    asyncio.run(main())
