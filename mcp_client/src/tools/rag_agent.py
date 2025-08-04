
from src.llm.oci_genai_agent import initialize_oci_genai_agent_service
@tool
def rag_agent_service(textinput) -> str:
    """Any questions about US Tax, use the rag_agent tool. Don't use search or Web_Scrapper for questions related to Tax"""
    generative_ai_agent_runtime_client, session_id = initialize_oci_genai_agent_service()
    response = generative_ai_agent_runtime_client.chat(
        agent_endpoint_id=agent_ep_id,
        chat_details=oci.generative_ai_agent_runtime.models.ChatDetails(
            user_message=textinput,
            session_id=session_id))

    # print(str(response.data))
    response = response.data.message.content.text
    return response