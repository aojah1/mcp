import asyncio, os
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.messages import HumanMessage
# For OCI GenAI Service
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_core.messages import AIMessage
from langchain_core.messages import AIMessage


def initialize_llm():
    try:
        # Set your OCI credentials
        compartment_id = "ocid1.compartment.oc1..aaaaaaaau6esoygdsqxfz6iv3u7ghvosfskyvd6kroucemvyr5wzzjcw6aaa"
        service_endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

        #model_id = "meta.llama-3.3-70b-instruct"
        model_id = "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyayjawvuonfkw2ua4bob4rlnnlhs522pafbglivtwlfzta"

        #model_id = "cohere.command-r-plus-08-2024"
        # Create an OCI Cohere LLM instance
        llm_oci = ChatOCIGenAI(
            model_id= model_id,  # Specify the model you want to use
            service_endpoint=service_endpoint,
            provider="meta",
            compartment_id=compartment_id,
            model_kwargs={"temperature": 0.7, "top_p": 0.75, "max_tokens": 1000}
        )
        return llm_oci
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        raise
# ---------- env / model ----------
venv_root = Path("/Users/aojah/PycharmProjects/mcp/.venv/.env")   # set automatically on activation

load_dotenv(venv_root)
#model = ChatOpenAI(model="gpt-4o")
model = initialize_llm()
# ---------- server descriptors ----------
BASE = (Path("~/PycharmProjects/mcp/mcp_server")
        .expanduser()
        .resolve())

math_server  = StdioServerParameters(
    command="python", args=[str(BASE / "math_server.py")]
)
stock_server = StdioServerParameters(
    command="python", args=[str(BASE / "stock_server.py")]
)
adb_server   = StdioServerParameters(
    command="/Applications/sqlcl/bin/sql", args=["-mcp"]
)

promt_oracle_db_operator = """This agent executes SQL queries in an Oracle database. 
    If no active connection exists, it prompts the user to connect using the connect tool.
    You should: Execute the provided SQL query.Return the results in CSV format.
    Args: sql: The SQL query to execute. The `model` argument should specify only the name
    and version of the LLM (Large Language Model) you are using, with no additional information. 
    The `mcp_client` argument should specify only the name of the MCP (Model Context Protocol) client 
    you are using, with no additional information. Returns: CSV-formatted query results. 
    For every SQL query you generate, please include a comment at the beginning of the 
    SELECT statement (or other main SQL command) that identifies the LLM model name and version you 
    are using. Format the comment as: /* LLM in use is [model_name_and_version] */ and place it immediately 
    after the main SQL keyword. For example: SELECT /* LLM in use is llama4-Maverick */ column1, 
    column2 FROM table_name; INSERT /* LLM in use is llama4-Maveric */ INTO table_name VALUES (...); 
    UPDATE /* LLM in use is llama4-Maveric */ table_name SET ...; 
    Please apply this format consistently to all SQL queries you generate, using your actual model name and version in the comment

"""

# Global Auto-Approve flag (will be set dynamically)
AUTO_APPROVE = 'N'  # Default to 'N'

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import asyncio

class RunSQLInput(BaseModel):
    sql: str = Field(description="The SQL query to execute.")
    model: str = Field(description="The name and version of the LLM (Large Language Model) you are using, with no additional information.")
    mcp_client: str = Field(description="The name of the MCP (Model Context Protocol) client you are using, with no additional information.")

def user_confirmed_tool(tool):
    async def wrapper(sql: str, model: str, mcp_client: str):
        sql_query = sql

        # Check Auto-Approve flag
        if AUTO_APPROVE == 'Y':
            approved = True
        else:
            print(f"\n\033[93mA SQL query is about to be executed by the agent:\033[0m")
            print(f"\033[97m{sql_query}\033[0m")
            confirmation = await asyncio.to_thread(input, "ALLOW this SQL execution? (y/n): ")
            approved = confirmation.lower() in {'y', 'yes'}

        if approved:
            # Call the original tool asynchronously if it supports it, else sync
            if hasattr(tool, 'ainvoke'):
                return await tool.ainvoke({"sql": sql, "model": model, "mcp_client": mcp_client})
            elif hasattr(tool, 'invoke'):
                return tool.invoke({"sql": sql, "model": model, "mcp_client": mcp_client})
            else:
                return tool.run(sql, model, mcp_client)
        else:
            # Return a message that instructs the agent to stop and finalize without retrying
            return "Error: SQL execution was aborted by the user. Do not attempt to run any more SQL queries or tools. Provide the final answer based on available information immediately."

    # Return as StructuredTool with coroutine for async support
    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=RunSQLInput,
        coroutine=wrapper,  # Use coroutine for async invocation
    )

async def main() -> None:
    async with AsyncExitStack() as stack:
        try:
            # 1. start each server, keep pipes open
            math_read,  math_write  = await stack.enter_async_context(stdio_client(math_server))
            stock_read, stock_write = await stack.enter_async_context(stdio_client(stock_server))
            adb_read, adb_write = await stack.enter_async_context(stdio_client(adb_server))

            # 2. open a ClientSession for each
            math_session  = await stack.enter_async_context(ClientSession(math_read,  math_write))
            stock_session = await stack.enter_async_context(ClientSession(stock_read, stock_write))
            adb_session = await stack.enter_async_context(ClientSession(adb_read, adb_write))

            # 3. handshake & discover tools
            await asyncio.gather(math_session.initialize(), stock_session.initialize(), adb_session.initialize())
            tools  = (await load_mcp_tools(math_session)) + (await load_mcp_tools(stock_session)) + (await load_mcp_tools(adb_session))

            # -------- Wrap SQL tools for user-in-the-loop confirmation -----------
            def is_sql_tool(tool):
                # Check for 'adb', 'sql', or 'oracle' in the tool name
                return any(kw in tool.name.lower() for kw in ["adb", "sql", "oracle"])

            wrapped_tools = []
            for t in tools:
                if is_sql_tool(t):
                    wrapped_tools.append(user_confirmed_tool(t))
                else:
                    wrapped_tools.append(t)
            # -----------------------------------------------------------------------

            # Prompt for Auto-Approve at the beginning, styled like the user input box
            global AUTO_APPROVE
            print("Do you want to auto-approve all SQL executions without prompting each time? (y/n):")
            confirmation = await asyncio.to_thread(input, "You: ")
            AUTO_APPROVE = 'Y' if confirmation.lower() in {'y', 'yes'} else 'N'

            # 4. build the agent
            agent = initialize_agent(
                tools=wrapped_tools,
                llm=model,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                handle_parsing_errors=True,
                verbose=True,
                agent_kwargs={"prefix": promt_oracle_db_operator},  # Pass the system message here
            )

            # ⏳ short-term memory (max 30 messages = 15 user + 15 AI)
            message_history = []

            # 5. interactive loop
            print("Type a question (empty / 'exit' to quit):")
            while True:
                user_input = await asyncio.to_thread(input, "You: ")
                if user_input.strip().lower() in {"exit", "quit"}:
                    print("👋  Bye!")
                    break

                # Add user's message
                message_history.append(HumanMessage(content=user_input))

                # Keep only the last 10 messages
                message_history = message_history[-30:]

                # Invoke agent
                ai_response = await agent.ainvoke({"input": message_history})
                msg = ai_response.get("output") if isinstance(ai_response, dict) else ai_response

                # Try to parse or wrap the output
                if isinstance(msg, AIMessage):
                    message_history.append(msg)
                    print(f"AI: {msg.content}\n")
                elif isinstance(msg, str):
                    ai_msg = AIMessage(content=msg)
                    message_history.append(ai_msg)
                    print(f"AI: {msg}\n")
                else:
                    print("AI: <<no response>>\n")

                # Trim history
                message_history = message_history[-30:]
        except Exception as e:
            print(f"\n❌ An error occurred during execution: {str(e)}")
            print("Please check your setup and try again. Exiting...")
            # Optional: Add any cleanup here if needed (e.g., close sessions manually)

if __name__ == "__main__":
    #grok()
    asyncio.run(main())