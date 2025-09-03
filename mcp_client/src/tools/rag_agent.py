from src.llm.oci_genai_agent import rag_agent_service
from langchain_core.tools import tool

@tool
def _rag_agent_service(inp: str):
    """RAG AGENT Service to answer questions from Knowledge base"""
    response  = rag_agent_service(inp)

    return response.data.message.content.text