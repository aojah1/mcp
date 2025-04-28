# ───────────────── mcp_chat_client.py ─────────────────
import asyncio
from contextlib import AsyncExitStack
from typing import List, Tuple, Awaitable, Callable

from dotenv import load_dotenv
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------- env / model ----------
load_dotenv()                      # pulls in OPENAI_API_KEY, etc.
MODEL_NAME = "gpt-4o"              # change if you like

# ---------- server descriptors ----------
SERVERS: List[StdioServerParameters] = [
    StdioServerParameters(command="python", args=["mcp_math_server.py"]),
    StdioServerParameters(command="python", args=["stock_server.py"]),
]


# ---------------- internal bootstrap -----------------
async def _startup() -> Tuple[object, Callable[[], Awaitable[None]]]:
    """
    Spin up all MCP servers, return (agent, async_shutdown_fn).
    """
    stack = AsyncExitStack()
    await stack.__aenter__()          # keep resources alive until shutdown()

    # 1. start each server, open ClientSession
    sessions = []
    for sp in SERVERS:
        read, write = await stack.enter_async_context(stdio_client(sp))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        sessions.append(session)

    # 2. gather tools
    tools = []
    for sess in sessions:
        tools.extend(await load_mcp_tools(sess))

    print("\nLoaded tools:")
    for t in tools:
        print("  🔧", t.name)
    print()

    # 3. build ReAct agent (default prompt already matches LangGraph vars)
    model = ChatOpenAI(model=MODEL_NAME)
    agent = create_react_agent(model, tools)

    async def _shutdown() -> None:
        await stack.aclose()

    return agent, _shutdown


# ---------------- module-level cache ------------------
_agent_singleton = None          # type: ignore
_shutdown_singleton = None       # type: ignore


async def init_agent():
    """Return the cached agent, starting servers on first call."""
    global _agent_singleton, _shutdown_singleton
    if _agent_singleton is None:
        _agent_singleton, _shutdown_singleton = await _startup()
    return _agent_singleton


async def shutdown_agent():
    """Terminate MCP subprocesses (call once on app exit)."""
    global _agent_singleton, _shutdown_singleton
    if _shutdown_singleton:
        await _shutdown_singleton()
    _agent_singleton = _shutdown_singleton = None


async def process_message(agent, user_text: str) -> str:
    """Send one user turn and return the assistant’s reply."""
    result = await agent.ainvoke({"messages": [HumanMessage(content=user_text)]})

    # The last entry may be a ToolMessage; grab the final AIMessage instead.
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            return msg.content
    return "<<no assistant response>>"
