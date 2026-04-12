import asyncio
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    SystemMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

async def run_agent(user_prompt: str):
    options = ClaudeAgentOptions(
        model="claude-haiku-4-5-20251001", # claude-3-haiku-20240307 (0.12) # claude-haiku-4-5-20251001
        cwd=PROJECT_DIR,
        env={
            "ANTHROPIC_API_KEY": "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"
        },
        setting_sources=["project", "user"],   # carica skill dal filesystem
        allowed_tools=[
            "Skill",
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "Bash",
            "WebSearch",
            "WebFetch",
        ],
    )

    async for message in query(prompt=user_prompt, options=options):
        if isinstance(message, SystemMessage):
            print(f"[SYSTEM] subtype={message.subtype} data={message.data}")

        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[TEXT] {block.text}")

                elif isinstance(block, ToolUseBlock):
                    print(f"[TOOL USE] {block.name} -> {block.input}")

                elif isinstance(block, ToolResultBlock):
                    print(f"[TOOL RESULT] {block.content}")

        elif isinstance(message, ResultMessage):
            print(f"[FINAL RESULT] {message.result}")
            print(f"[COST USD] {message.total_cost_usd}")

asyncio.run(
    run_agent(
        "Usando la skill di search_norma rispondi a questo quesito: "
        """[ALF A], di seguito anche istante, fa presente quanto nel prosieguo sinteticamente
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
    )
)