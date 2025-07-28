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


# ---------- env / model ----------
venv_root = Path("/Users/aojah/PycharmProjects/mcp/.venv/.env")   # set automatically on activation

load_dotenv(venv_root)
model = ChatOpenAI(model="gpt-4o")

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

async def main() -> None:
    async with AsyncExitStack() as stack:
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



        # 4. build the agent
        agent = create_react_agent(model, tools)


        # ⏳ short-term memory (max 10 messages = 5 user + 5 AI)
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
            message_history = message_history[-10:]

            # Invoke agent with current history
            ai_response = await agent.ainvoke({"messages": message_history})

            # Add AI response to history
            for msg in reversed(ai_response["messages"]):
                if isinstance(msg, AIMessage):
                    message_history.append(msg)
                    message_history = message_history[-10:]  # Trim again after appending
                    print(f"AI: {msg.content}\n")
                    break
            else:
                print("AI: <<no response>>\n")



if __name__ == "__main__":
    #grok()
    asyncio.run(main())
