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
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_core.messages import AIMessage
from src.llm.oci_genai import initialize_llm
from src.prompt_engineering.topics.db_operator import promt_oracle_db_operator
from src.llm.oci_genai_agent import rag_agent_service
from langchain_core.tools import tool

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

# ────────────────────────────────────────────────────────
# 2) Logic
# ────────────────────────────────────────────────────────
# ---------- Initialize a LLama model ----------
model = initialize_llm()

# ---------- server descriptors ----------
adb_server = StdioServerParameters(
    command="/Applications/sqlcl/bin/sql", args=["-mcp"]
)


# Global Auto-Approve flag (will be set dynamically)
AUTO_APPROVE = 'N'  # Default to 'N'

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import asyncio

class RunSQLInput(BaseModel):
    sql: str = Field(default="select sysdate from dual", description="The SQL query to execute.")
    model: str = Field(default="oci/generativeai-chat:2024-05-01", description="The name and version of the LLM (Large Language Model) you are using.")
    mcp_client: str = Field(default="sqlcl", description="The name of the MCP (Model Context Protocol) client you are using.")

def user_confirmed_tool(tool):
    async def wrapper(sql: str, model: str = None, mcp_client: str = None):
        sql_query = sql

        # Fill in default values if missing
        model = model or "oci/generativeai-chat:2024-05-01"
        mcp_client = mcp_client or "sqlcl"

        # Check Auto-Approve flag
        if AUTO_APPROVE == 'Y':
            approved = True
        else:
            print(f"\n\033[93mA SQL query is about to be executed by the agent:\033[0m")
            print(f"\033[97m{sql_query}\033[0m")
            confirmation = await asyncio.to_thread(input, "ALLOW this SQL execution? (y/n): ")
            approved = confirmation.lower() in {'y', 'yes'}

        if approved:
            payload = {"sql": sql_query, "model": model, "mcp_client": mcp_client}
            if hasattr(tool, 'ainvoke'):
                return await tool.ainvoke(payload)
            elif hasattr(tool, 'invoke'):
                return tool.invoke(payload)
            else:
                return tool.run(**payload)
        else:
            return "Error: SQL execution was aborted by the user. Do not attempt to run any more SQL queries or tools. Provide the final answer based on available information immediately."

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=RunSQLInput,
        coroutine=wrapper,
    )


@tool
def _rag_agent_service(inp: str):
    """RAG AGENT"""
    response  = rag_agent_service(inp)

    return response.data.message.content.text

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

        try:
            # Load tools
            tools = []
            if adb_session:
                tools = await load_mcp_tools(adb_session)
            tools += [_rag_agent_service]  # Always add RAG tool

            # Wrap SQL tools for user confirmation
            def is_sql_tool(tool):
                return any(kw in tool.name.lower() for kw in ["adb", "sql", "oracle"])

            wrapped_tools = []
            for t in tools:
                if is_sql_tool(t):
                    wrapped_tools.append(user_confirmed_tool(t))
                else:
                    wrapped_tools.append(t)

            # Prompt for auto-approval
            global AUTO_APPROVE
            print("Do you want to auto-approve all SQL executions without prompting each time? (y/n):")
            confirmation = await asyncio.to_thread(input, "You: ")
            AUTO_APPROVE = 'Y' if confirmation.lower() in {'y', 'yes'} else 'N'

            # Initialize agent
            agent = initialize_agent(
                tools=wrapped_tools,
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
                    msg = ai_response.get("output") if isinstance(ai_response, dict) else ai_response
                    if isinstance(msg, AIMessage):
                        message_history.append(msg)
                        print(f"AI: {msg.content}\n")
                    elif isinstance(msg, str):
                        ai_msg = AIMessage(content=msg)
                        message_history.append(ai_msg)
                        print(f"AI: {msg}\n")
                    else:
                        print("AI: <<no response>>\n")
                except Exception as agent_err:
                    print(f"⚠️  Agent failed to respond: {agent_err}")
        except Exception as final_err:
            print(f"\n❌ Unhandled error: {final_err}")


if __name__ == "__main__":
    #grok()
    asyncio.run(main())