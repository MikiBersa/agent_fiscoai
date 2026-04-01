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
from src.graph.research.state import Fonte
from langchain.agents import AgentState


class PlanExecute(AgentState):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    response_moment: str
    thinker: str
    list_fonte: Annotated[List[Fonte], operator.add]


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

    # response_moment

    #agent_response = await search_agent.ainvoke(
    #    {"messages": [("user", task_formatted)]}
    #)

    agent_response = await rag_search_agent.ainvoke(
        {"messages": [{"role": "user", "content": task_formatted}], "list_fonte": state["list_fonte"], "summary": ""}
    )

    summary_moment = state["response_moment"] + "\n"+"="*80+"\n" +task_formatted.replace("You are", "It is")+ "\n\n"+ agent_response["summary"] + "\n"+"="*80+"\n"

    return {
        "past_steps": [(task, agent_response["summary"])],
        "list_fonte": agent_response["list_fonte"],
        "response_moment": summary_moment,
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

# TODO METTERE QUI IL TESTO
async def thinker_step(state: PlanExecute):
    thinker_response = await thinker.ainvoke({"messages": state["messages"], "response_moment": state["response_moment"]})
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
        thread = {"configurable": {"thread_id": "5"}}
        inputs = {"input": """L'Istante, in qualità di titolare di una ditta individuale rappresenta di svolgere
attività come studio di consulenza per la circolazione dei mezzi di trasporto e
dichiara che presso lo studio medesimo sono operativi sia lo ''Sportello Telematico
dell'Automobilista'' (STA), sia lo ''Sportello Telematico del Diportista'' (STED).
Al riguardo, fa presente di svolgere in via esclusiva l'attività di gestione
delle pratiche amministrative relative alla nautica da diporto, gran parte delle quali
rappresentate dai passaggi di proprietà di unità superiori ai 10 metri e, quindi, iscritte
negli appositi registri.
Pagina 2 di 8
L'Istante riferisce che sulla base di quanto previsto dall'articolo 7 del decreto
legge 4 luglio 2006, n. 223, convertito con modificazioni dalla legge 4 agosto 2006, n.
248, avente ad oggetto misure urgenti in materia di passaggi di proprietà di beni mobili
registrati, i passaggi di proprietà delle imbarcazioni da diporto avvengono tramite atti
sui quali autentica la firma delle parti contraenti, nel rispetto della previsione recata dalla
disposizione richiamata.
Atteso che tra i soggetti obbligati a richiedere la registrazione, l'articolo 10 del
d.P.R. 26 aprile 1986, n. 131, al comma 1, lettera b) contempla «i notai, gli ufficiali
giudiziari, i segretari o delegati della pubblica amministrazione e gli altri pubblici
ufficiali per gli atti da essi redatti, ricevuti o autenticati», l'Istante chiede se tra gli stessi
rientrano anche i titolari di STA e STED relativamente all'autentica apposta sull'atto di
compravendita del bene mobile registrato.
In sede di documentazione integrativa, l'Istante ha precisato che dal 2021 è
operativo l'''Archivio Telematico Centrale'' (ATCN) e «La registrazione, oltre ad essere
obbligatoria, è, in ogni caso, indispensabile per procedere alle trascrizioni da parte
dello STED nell'Archivio Telematico Centrale».""", 
            "response_moment": ""}

        async for event in todo_workflow.astream(inputs, config=thread):
            for k, v in event.items():
                if k != "__end__":
                    print(v)
                    print("="*80)

    asyncio.run(main())
