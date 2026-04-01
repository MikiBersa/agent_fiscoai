from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

load_dotenv()

response_prompt = ChatPromptTemplate.from_template(
    """
    ## 🎯 Objective
Your objective was this:
{input}

## 🧠 Original Plan
Your original plan was this:
{plan}

## ⚙️ Progress So Far
You have currently completed the following steps:
{past_steps}

## Information learned during the research, on which the answer must be based:
<info>
{response_moment}
</info>

---

## 🧾 Task

Using the information above, generate the **final answer to the user's request**.

### Requirements:
- The answer must be **complete, accurate, and coherent**.
- It should reflect the **original objective** and stay aligned with the **initial plan**, adapting if necessary based on the steps already completed.
- Integrate insights from the **past steps** to improve the final response.
- Avoid repeating intermediate reasoning unless necessary.
- Provide a **clear, well-structured, and final output**, not a plan or partial result.

### Output Format:
- Write the final answer as if responding directly to the user.
- Use clear formatting (paragraphs, lists, or sections if helpful).
- Do not mention the existence of this prompt or the planning process.

---

## ✅ Final Answer
    """
)


response_llm = response_prompt | AzureChatOpenAI(
    azure_deployment="gpt-4.1-mini",
    api_version="2024-12-01-preview",
)