"""
streamlit_app.py
────────────────
Run with:  streamlit run streamlit_app.py
"""
import asyncio, atexit
import streamlit as st

import mcp_chat_client as mcp

st.set_page_config(page_title="Multi-Server MCP Chat", page_icon="🤖", layout="centered")
st.title("🤖 Multi-Server MCP Chat")

# ─────────────────────────  bootstrap agent  ─────────────────────────
@st.cache_resource(show_spinner="Launching MCP servers… this takes a few seconds.")
def get_agent():
    return asyncio.run(mcp.init_agent())

agent = get_agent()

# clean shutdown when the Python process exits
atexit.register(lambda: asyncio.run(mcp.shutdown_agent()))
# ─────────────────────────────────────────────────────────────────────

# session-state chat history
hist = st.session_state.setdefault("history", [])

def do_rerun():
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    elif hasattr(st, "rerun"):
        st.rerun()
    else:
        st.warning("Streamlit too old for rerun; please upgrade.")
        st.stop()

# input box
if prompt := st.chat_input("Ask me anything…"):
    hist.append(("user", prompt))
    do_rerun()

# replay history & decide if we owe a reply
needs_reply = hist and hist[-1][0] == "user"
for role, msg in hist:
    with st.chat_message(role):
        st.markdown(msg)

if needs_reply:
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("…thinking…")

        assistant_text = asyncio.run(mcp.process_message(agent, hist[-1][1]))

        placeholder.markdown(assistant_text)
        hist.append(("assistant", assistant_text))
        do_rerun()
