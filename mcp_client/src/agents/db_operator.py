"""
oracledb_operator.py
Author: Anup Ojah
Date: 2025-23-18
=================================
==Oracle Database Operator==
==================================
This agent integrates with Oracle DB SQLCl MCP Server, allowing NL conversation with any Oracle Database (19 c or higher).
https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.2/sqcug/using-oracle-sqlcl-mcp-server.html
Workflow Overview:
1. Load config and credentials from .env
2. Start MCP clients for SQLCL
3. Register tools with the agent
4. Run the agent with user input and print response
"""

import asyncio, os
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from pathlib import Path
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.messages import HumanMessage
# For OCI GenAI Service
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_core.messages import AIMessage
from src.llm.oci_genai import initialize_llm
from src.prompt_engineering.topics.db_operator import promt_oracle_db_operator
from src.tools.rag_agent import _rag_agent_service
from src.tools.python_scratchpad import run_python
from langchain_core.tools import tool
from langchain_core.agents import AgentFinish
import matplotlib
matplotlib.use("Agg")
import warnings
warnings.filterwarnings("ignore")

# ────────────────────────────────────────────────────────
# 1) bootstrap paths + env + llm
# ────────────────────────────────────────────────────────
THIS_DIR = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parent.parent.parent

load_dotenv(PROJECT_ROOT / "config/.env")  # expects OCI_ vars in .env

# Set up the OCI GenAI Agents endpoint configuration
OCI_CONFIG_FILE = os.getenv("OCI_CONFIG_FILE")
OCI_PROFILE = os.getenv("OCI_PROFILE")
AGENT_EP_ID = os.getenv("AGENT_EP_ID")
AGENT_SERVICE_EP = os.getenv("AGENT_SERVICE_EP")
AGENT_KB_ID = os.getenv("AGENT_KB_ID")
AGENT_REGION = os.getenv("AGENT_REGION")
SQLCLI_MCP_PROFILE = os.getenv("SQLCLI_MCP_PROFILE")
TAVILY_MCP_SERVER = os.getenv("TAVILY_MCP_SERVER")
FILE_SYSTEM_ACCESS_KEY=os.getenv("FILE_SYSTEM_ACCESS_KEY")
print(FILE_SYSTEM_ACCESS_KEY)

# ────────────────────────────────────────────────────────
# 2) Logic
# ────────────────────────────────────────────────────────
# ---------- Initialize a LLama model ----------
model = initialize_llm()

# ---------- server descriptors ----------
adb_server = StdioServerParameters(
    command=SQLCLI_MCP_PROFILE, args=["-mcp"]
)

# Use npx
local_file_server= StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", FILE_SYSTEM_ACCESS_KEY])

# Use npx
tavily_server = StdioServerParameters(
    command="npx",
    args=["-y", "mcp-remote", TAVILY_MCP_SERVER])

# Global Auto-Approve flag (will be set dynamically)
AUTO_APPROVE = 'N'  # Default to 'N'

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import asyncio

class RunSQLInput(BaseModel):
    sql: str = Field(default="select sysdate from dual", description="The SQL query to execute.")
    model: str = Field(default="oci/generativeai-chat:2024-05-01", description="The name and version of the LLM (Large Language Model) you are using.")
    sqlcl: str = Field(default="sqlcl", description="The name or path of the SQLcl MCP client.")  # Changed from mcp_client to sqlcl

def user_confirmed_tool(tool):
    async def wrapper(*args, **kwargs):
        # Support raw string input or keyword arguments (from structured agent)
        if args and isinstance(args[0], str):
            sql_query = args[0]
            model = "oci/generativeai-chat:2024-05-01"
            sqlcl_param = "sqlcl"  # Default
        else:
            sql_query = kwargs.get("sql", "select sysdate from dual")
            model = kwargs.get("model", "oci/generativeai-chat:2024-05-01")
            sqlcl_param = kwargs.get("sqlcl", "sqlcl")  # Changed key to sqlcl

        # Debug logging
        print(f"DEBUG: Preparing payload - SQL: {sql_query}, Model: {model}, SQLCL: {sqlcl_param}")

        if AUTO_APPROVE == 'Y':
            approved = True
        else:
            print(f"\n\033[93mA SQL query is about to be executed by the agent:\033[0m")
            print(f"\033[97m{sql_query}\033[0m")
            confirmation = await asyncio.to_thread(input, "ALLOW this SQL execution? (y/n): ")
            approved = confirmation.lower() in {'y', 'yes'}

        if approved:
            payload = {
                "sql": sql_query,
                "model": model,
                "sqlcl": sqlcl_param  # Changed key to sqlcl
            }
            try:
                if hasattr(tool, 'ainvoke'):
                    return await tool.ainvoke(payload)
                elif hasattr(tool, 'invoke'):
                    return tool.invoke(payload)
                else:
                    return tool.run(**payload)
            except Exception as e:
                return f"ERROR: Failed to execute SQLcl tool - {str(e)}\nIf 'sqlcl parameter is required', ensure SQLcl is installed and in PATH."
        else:
            return "⚠️ Execution cancelled by user."

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=RunSQLInput,
        coroutine=wrapper,
    )



async def main() -> None:
    async with AsyncExitStack() as stack:
        adb_session = None  # Default in case connection fails

        # Attempt SQLCL MCP connection
        try:
            adb_read, adb_write = await stack.enter_async_context(stdio_client(adb_server))
            adb_session = await stack.enter_async_context(ClientSession(adb_read, adb_write))
            await adb_session.initialize()
        except Exception as conn_err:
            print(f"\n❌ Could not connect to Oracle SQLCL MCP Server: {conn_err}")
            print("⚠️  You can continue asking questions, but SQL tools will be unavailable.\n")

        # Attempt Tavily MCP connection
        try:
            tavily_read, tavily_write = await stack.enter_async_context(stdio_client(tavily_server))
            tavily_server_session = await stack.enter_async_context(ClientSession(tavily_read, tavily_write))
            await tavily_server_session.initialize()
        except Exception as tavily_conn_err:
            print(f"\n❌ Could not connect to Tavily MCP Server: {tavily_conn_err}")
            print("⚠️  You can continue asking questions, but Tavily tools will be unavailable.\n")

        # Attempt Local File Server MCP connection
        try:
            local_file_read, local_file_write = await stack.enter_async_context(stdio_client(local_file_server))
            local_file_session = await stack.enter_async_context(ClientSession(local_file_read, local_file_write))
            await local_file_session.initialize()
        except Exception as tavily_conn_err:
            print(f"\n❌ Could not connect to Local File Server MCP Server: {tavily_conn_err}")
            print("⚠️  You can continue asking questions, but Local File Server tools will be unavailable.\n")

        try:
            # Load tools
            mcp_tools = []

            # original_tools = [await load_mcp_tools(adb_session), await load_mcp_tools(tavily_server_session)]
            if adb_session is not None:
                mcp_tools.extend(await load_mcp_tools(adb_session))

            if 'tavily_server_session' in locals() and tavily_server_session is not None:
                mcp_tools.extend(await load_mcp_tools(tavily_server_session))

            if 'local_file_session' in locals() and local_file_session is not None:
                mcp_tools.extend(await load_mcp_tools(local_file_session))
            
            tools = []

            def is_sql_tool(tool):
                return any(kw in tool.name.lower() for kw in ["adb", "sql", "oracle"])

            for t in mcp_tools:
                if is_sql_tool(t):
                    wrapped = user_confirmed_tool(t)
                    wrapped.name = t.name  # overwrite name so "run-sqlcl" matches
                    tools.append(wrapped)
                else:
                    tools.append(t)

            tools.append(run_python)  # Add your Python tool
            tools.append(_rag_agent_service)  # Add your RAG tool

            print(f"✅ Registered tools: {[t.name for t in tools]}")

            # Prompt for auto-approval
            global AUTO_APPROVE
            print("Do you want to auto-approve all SQL executions without prompting each time? (y/n):")
            confirmation = await asyncio.to_thread(input, "You: ")
            AUTO_APPROVE = 'Y' if confirmation.lower() in {'y', 'yes'} else 'N'

            # Initialize agent
            agent = initialize_agent(
                tools=tools,
                llm=model,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                handle_parsing_errors=True,
                verbose=True,
                agent_kwargs={"prefix": promt_oracle_db_operator},
            )

            message_history = []
            print("Type a question (empty / 'exit' to quit):")
            while True:
                user_input = await asyncio.to_thread(input, "You: ")
                if user_input.strip().lower() in {"exit", "quit"}:
                    print("👋  Bye!")
                    break

                message_history.append(HumanMessage(content=user_input))
                message_history = message_history[-30:]

                try:
                    ai_response = await agent.ainvoke({"input": message_history})

                    # Improved output extraction
                    if isinstance(ai_response, dict):
                        msg = ai_response.get("output")
                    elif isinstance(ai_response, AgentFinish):
                        # Handle AgentFinish: extract from return_values
                        msg = ai_response.return_values.get("output")
                    else:
                        msg = ai_response  # Fallback for other types

                    # Now process and print
                    if isinstance(msg, AIMessage):
                        message_history.append(msg)
                        print(f"AI: {msg.content}\n")
                    elif isinstance(msg, str):
                        ai_msg = AIMessage(content=msg)
                        message_history.append(ai_msg)
                        print(f"AI: {msg}\n")
                    elif isinstance(msg, dict) and "content" in msg:
                        # Handle if it's a dict with 'content' (e.g., parsed Final Answer)
                        ai_msg = AIMessage(content=msg.get("content", "<<no content>>"))
                        message_history.append(ai_msg)
                        print(f"AI: {ai_msg.content}\n")
                    else:
                        print("AI: <<no response>>\n")  # Only fallback if truly nothing
                except Exception as agent_err:
                    print(f"⚠️  Agent failed to respond: {agent_err}")
        except Exception as final_err:
            print(f"\n❌ Unhandled error: {final_err}")


if __name__ == "__main__":
    #grok()
    asyncio.run(main())