from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch

load_dotenv()


tools = [TavilySearch(max_results=3)]

# Choose the LLM that will drive the agent
model = init_chat_model(
    "azure_openai:gpt-4.1-mini",  # nome modello lato LangChain
    azure_deployment="gpt-4.1-mini",  # oppure il nome reale del deployment Azure
)
prompt = "You are a helpful assistant."

search_agent = create_agent(
    model,
    tools,
    system_prompt=prompt,
).with_config(
    {"recursion_limit": 25}
)  # recursion_limit limits the number of steps the agent will run
