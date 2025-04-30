import asyncio, os
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from pathlib import Path

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.messages import HumanMessage

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
    command="python", args=[str(BASE / "adb_server.py")]
)

async def main() -> None:
    async with AsyncExitStack() as stack:
        # 1. start each server, keep pipes open
        math_read,  math_write  = await stack.enter_async_context(stdio_client(math_server))
        stock_read, stock_write = await stack.enter_async_context(stdio_client(stock_server))
        #adb_read, adb_write = await stack.enter_async_context(stdio_client(adb_server))

        # 2. open a ClientSession for each
        math_session  = await stack.enter_async_context(ClientSession(math_read,  math_write))
        stock_session = await stack.enter_async_context(ClientSession(stock_read, stock_write))
       # adb_session = await stack.enter_async_context(ClientSession(adb_read, adb_write))

        # 3. handshake & discover tools
        await asyncio.gather(math_session.initialize(), stock_session.initialize())
        tools  = (await load_mcp_tools(math_session)) + (await load_mcp_tools(stock_session))#+ (await load_mcp_tools(adb_session))

        # 4. build the agent
        agent = create_react_agent(model, tools)

        # 5. interactive loop
        print("Type a question (empty / 'exit' to quit):")
        while True:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.strip().lower() in {"", "exit", "quit"}:
                print("👋  Bye!")
                break

            ai_response = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_input)]}
            )
            last_ai_msg = ai_response["messages"][-1].content
            print(f"AI: {last_ai_msg}\n")

if __name__ == "__main__":
    asyncio.run(main())
