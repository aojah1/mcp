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

def grok():
    # coding: utf-8
    # Copyright (c) 2023, Oracle and/or its affiliates.  All rights reserved.
    # This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.

    ##########################################################################
    # chat_demo.py
    # Supports Python 3
    ##########################################################################
    # Info:
    # Get texts from LLM model for given prompts using OCI Generative AI Service.
    ##########################################################################
    # Application Command line(no parameter needed)
    # python chat_demo.py
    ##########################################################################
    import oci

    # Setup basic variables
    # Auth Config
    # TODO: Please update config profile name and use the compartmentId that has policies grant permissions for using Generative AI Service
    compartment_id = "ocid1.compartment.oc1..aaaaaaaau6esoygdsqxfz6iv3u7ghvosfskyvd6kroucemvyr5wzzjcw6aaa"
    CONFIG_PROFILE = "DEFAULT"
    config = oci.config.from_file('~/.oci/config', CONFIG_PROFILE)

    # Service endpoint
    endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

    generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(config=config,
                                                                                             service_endpoint=endpoint,
                                                                                             retry_strategy=oci.retry.NoneRetryStrategy(),
                                                                                             timeout=(10, 240))
    chat_detail = oci.generative_ai_inference.models.ChatDetails()

    content = oci.generative_ai_inference.models.TextContent()
    content.text = "i love coding"
    message = oci.generative_ai_inference.models.Message()
    message.role = "USER"
    message.content = [content]

    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = [message]
    chat_request.max_tokens = 20000
    chat_request.temperature = 1
    chat_request.frequency_penalty = 0
    chat_request.presence_penalty = 0
    chat_request.top_p = 1

    chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(
        model_id="ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceya6dvgvvj3ovy4lerdl6fvx525x3yweacnrgn4ryfwwcoq")
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = compartment_id

    chat_response = generative_ai_inference_client.chat(chat_detail)

    # Print result
    print("**************************Chat Result**************************")
    print(vars(chat_response))

    return generative_ai_inference_client

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
    after the main SQL keyword. For example: SELECT /* LLM in use is llama3.3-70B */ column1, 
    column2 FROM table_name; INSERT /* LLM in use is llama3.3-70B */ INTO table_name VALUES (...); 
    UPDATE /* LLM in use is llama3.3-70B */ table_name SET ...; 
    Please apply this format consistently to all SQL queries you generate, using your actual model name and version in the comment

"""

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
        #agent = create_react_agent(model, tools)
        # Initialize an agent using:
        # - The defined tools
        # - The Cohere LLM
        # - A ReAct-style agent type that allows the LLM to decide what tool to call step-by-step
        # - verbose=True to print internal thought process

        agent = initialize_agent(
            tools=tools,
            llm=model,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION  ,
            handle_parsing_errors=True,
            verbose=True,
        )

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

            from langchain_core.messages import AIMessage

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
            message_history = message_history[-10:]


if __name__ == "__main__":
    #grok()
    asyncio.run(main())
