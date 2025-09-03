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
    import oci, os

    # ─── OCI LLM ──────────────────────────────────────────
    from langchain_community.chat_models import ChatOCIGenAI
    from dotenv import load_dotenv

    # ────────────────────────────────────────────────────────
    # 1) bootstrap paths + env + llm
    # ────────────────────────────────────────────────────────
    THIS_DIR     = Path(__file__).resolve()
    PROJECT_ROOT = THIS_DIR.parent.parent.parent
    print(PROJECT_ROOT)
    load_dotenv(PROJECT_ROOT / "config/.env")

    #────────────────────────────────────────────────────────
    # OCI GenAI configuration
    # ────────────────────────────────────────────────────────
    COMPARTMENT_ID  = os.getenv("OCI_COMPARTMENT_ID")
    ENDPOINT        = os.getenv("OCI_GENAI_ENDPOINT")
    OCI_CONFIG_FILE = os.getenv("OCI_CONFIG_FILE")
    OCI_GENAI_MODEL_ID_GROK = os.getenv("OCI_GENAI_MODEL_ID_GROK")

    generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(config=OCI_CONFIG_FILE,
                                                                                             service_endpoint=ENDPOINT,
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
        model_id=OCI_GENAI_MODEL_ID_GROK)
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = COMPARTMENT_ID

    chat_response = generative_ai_inference_client.chat(chat_detail)

    # Print result
    print("**************************Chat Result**************************")
    print(vars(chat_response))

    return generative_ai_inference_client