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
from src.graph.research.tools import summary_writing


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


def execute_step(state: PlanExecute):
    plan = state["plan"]

    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    task = plan[0]

    task_formatted = f"""For the following plan:
    {plan_str}\n\nYou are tasked with executing step {1}, {task}."""

    # response_moment

    #agent_response = await search_agent.ainvoke(
    #    {"messages": [("user", task_formatted)]}
    #)

    agent_response = rag_search_agent.invoke(
        {"messages": [{"role": "user", "content": task_formatted}], "list_fonte": state["list_fonte"], "summary": ""}
    )

    summary_response = summary_writing(state["list_fonte"])

    summary_moment = state["response_moment"] + "\n"+"="*80+"\n" +task_formatted.replace("You are", "It is")+ "\n\n"+ summary_response + "\n"+"="*80+"\n"

    return {
        "past_steps": [(task, summary_response)],
        "list_fonte": agent_response["list_fonte"],
        "response_moment": summary_moment,
    }


async def plan_step(state: PlanExecute):
    plan = await planner.ainvoke({
        "messages": state["messages"],
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
        thread = {"configurable": {"thread_id": "10"}}
        input = """ALF A], di seguito anche istante, fa presente quanto nel prosieguo sinteticamente
riportato.
L'istante è una società in house della Regione [...] ­ costituita il [...] 2003, ai sensi
dell'articolo 40 della Legge Regionale [...] e successive modifiche ­ posseduta al 53,5%
dalla stessa Regione e per il restante 46,5% dalla medesima [ALF A].
A seguito di Deliberazione n. [...] del 2022 ­ con cui si dispone l'affidamento,
in favore dell'istante, del Servizio Idrico Integrato (''SII'') per i segmenti: captazione
e adduzione acque potabili, distribuzione, fognatura e depurazione per l'intera
circoscrizione regionale per un arco temporale di 30 anni, con decorrenza dal 1° gennaio
Pagina 2 di 5
2023 ­ con il successivo Accordo operativo di cui al repertorio n. [...] del [...] 2023, la
società si è, quindi, obbligata nei confronti del Comune [...] ad emettere in nome proprio
le fatture relative al SII nei confronti dei clienti finali.
Ciò premesso, l'istante chiede conferma circa «l'applicabilità alla fattispecie in
esame dell'art. 2 del Decreto [ministeriale 24 ottobre 2000, n. 370, ndr], nella parte
in cui prevede che, per il servizio di somministrazione di acqua, si possa limitarsi ad
annotare nel registro dei corrispettivi di cui all'art. 24 del Decreto IVA l'ammontare
dei corrispettivi riscossi, laddove l'annotazione delle ''bollette/fatture''
, ancorché emesse
elettronicamente, non determinerebbe alcun effetto di anticipazione dell'esigibilità
dell'imposta ex art. 6, comma 2, Decreto IVA»."""
        inputs = {"messages": [("user", input)], 
            "response_moment": "", "input": input}

        async for event in todo_workflow.astream(inputs, config=thread):
            for k, v in event.items():
                if k != "__end__":
                    print(v)
                    print("="*80)

    asyncio.run(main())
