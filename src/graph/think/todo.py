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
from src.graph.research.tools import summary_writing, summary_writing_summary, responce_writing


class PlanExecute(AgentState):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    response_moment: str
    thinker: str
    # list_fonte: Annotated[List[Fonte], operator.add]
    list_fonte: List[Fonte]


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

User-posted question:
<QUESTION>
{input}
</QUESTION>

At each step you must take the original question but write it differently based on what you need to research or delve into.

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
- Use Italian language
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

    At each step you must take the original question but write it differently based on what you need to research or delve into.
    - Use Italian language
    - Do not add steps that have already been done
    
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
        {"messages": [{"role": "user", "content": task_formatted}], "list_fonte": state.get("list_fonte", []), "summary": "", "input": state["input"]}
    )

    print("RICERCA: ", len(agent_response["list_fonte"]))
    summary_moment = summary_writing(agent_response["list_fonte"])

    # summary_moment = state["response_moment"] + "\n"+"="*80+"\n" +task_formatted.replace("You are", "It is")+ "\n\n"+ summary_response + "\n"+"="*80+"\n"

    if len(state["list_fonte"]) > 25:
        summary_moment = summary_writing_summary(summary_moment)

    steps = state["past_steps"]
    steps.append((task, summary_moment))
    
    # PORTARE AVANTI IL RAGIONAMENTO NELLA RICERCA
    response_moment = responce_writing(
        steps,
        state["response_moment"],
        state["input"],
    )

    return {
        "past_steps": [(task, summary_moment)],
        "list_fonte": agent_response["list_fonte"],
        "response_moment": response_moment,
    }


async def plan_step(state: PlanExecute):
    plan = await planner.ainvoke({
        "thinker": state.get("thinker", ""), "input": state["input"]
    })
    return {"plan": plan.steps}


async def replan_step(state: PlanExecute):
    # QUI METTERE UN LIMITE NEL REPLANNING

    output = await replanner.ainvoke(state)

    if isinstance(output.action, Response):
        output = await response_llm.ainvoke(state)
        return {"response": output.content}
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

# METTERE QUI IL TESTO
async def thinker_step(state: PlanExecute):
    print("LEN POST STEPS", len(state["past_steps"]))
    thinker_response = await thinker.ainvoke({"response_moment": state["response_moment"], "input": state["input"], "planning": state["plan"]})
    return {"thinker": thinker_response.content}


workflow = StateGraph(PlanExecute)

workflow.add_node("pre_thinker", thinker_step)
workflow.add_node("post_thinker", thinker_step)
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_step)
workflow.add_node("replan", replan_step)

# STRUTTURA DEL GRAFO
workflow.add_edge(START, "pre_thinker")
workflow.add_edge("pre_thinker", "planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "post_thinker")
workflow.add_edge("post_thinker", "replan")

# INSERIRE UNA SEZIONE IN CUI VIENE PRESO DOMANDA E RISPOSTA DEL'UTENTE DA FARE A LUI

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
        thread = {"configurable": {"thread_id": "50"}}
        input = """ALFA (di seguito,
''Istante'' o la ''Società''), con l'istanza di interpello in oggetto,
chiede chiarimenti in merito alla determinazione della base imponibile del contributo di
solidarietà temporaneo dovuto per l'anno 2023, introdotto dall'articolo 1, commi da 115 a
121, della legge 29 dicembre 2022, n. 197 (di seguito, anche, ''Legge di Bilancio 2023'').
La Società, «attiva nel settore della distribuzione petrolifera [...] con il brand ''...
'' utilizzato nelle [n.d.r. proprie] stazioni di servizio», dichiara di rientrare «fra i soggetti
individuati dall'art. 1, comma 115 della Legge di Bilancio 2023 [...] tenuti al pagamento
del contributo straordinario sul c.d. extraprofitto, generato dall'aumento dei prezzi e
Pagina 2 di 13
delle tariffe nel settore energetico» e rappresenta di aver ricevuto, nel dicembre del 2022,
«un ristoro da parte di [...], relativo ad una controversia sorta [...] circa trenta anni fa».
Detto ristoro, confermato dapprima dalla Corte d'Appello [...], e successivamente
dalla Corte di Cassazione [...] ammonta a complessivi euro [...] ed è stato riconosciuto «a
ristoro della perdita per il mancato guadagno in relazione ai prodotti commercializzati,
rettificando i coefficienti relativi ai margini e ai pesi applicati alle quantità prodotte».
Inoltre, la Società evidenzia che «al termine della controversia, sulla base di
quanto ci è stato rappresentato per le vie brevi, la Società ha ricevuto da parte di [...],
il bonifico per il ristoro di dette somme, lo scorso mese di dicembre 2022».
Tanto premesso, l'Istante chiede se «la corresponsione di detto importo sia
rilevante ai fini del calcolo del contributo di solidarietà temporaneo per il 2023,
conformemente alle modalità di determinazione della base imponibile previste dalla
norma»."""
        inputs = {"messages": [("user", input)], 
            "response_moment": "", "input": input, "list_fonte": [], "plan": []}

        async for event in todo_workflow.astream(inputs, config=thread):
            for k, v in event.items():
                if k != "__end__":
                    print(v)
                    print("="*80)

    asyncio.run(main())
