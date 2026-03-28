from daytona import Daytona, DaytonaConfig

from langchain_daytona import DaytonaSandbox

from dotenv import load_dotenv

load_dotenv()
import os

config = DaytonaConfig(api_key=os.getenv("DYTONA_API_KEY"))

sandbox = Daytona(config).create()
backend = DaytonaSandbox(sandbox=sandbox)

result = backend.execute("python --version")
print(result.output)