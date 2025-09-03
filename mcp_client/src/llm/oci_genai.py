import os
from pathlib import Path
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
COMPARTMENT_ID = os.getenv("OCI_COMPARTMENT_ID")
ENDPOINT       = os.getenv("OCI_GENAI_ENDPOINT")
MODEL_ID       = os.getenv("OCI_GENAI_MODEL_ID")
PROVIDER       = os.getenv("PROVIDER")
AUTH_TYPE      = "API_KEY"
OCI_PROFILE = os.getenv("OCI_PROFILE")


def initialize_llm():
    try:
        return ChatOCIGenAI(
            model_id=MODEL_ID,
            service_endpoint=ENDPOINT,
            compartment_id=COMPARTMENT_ID,
            provider=PROVIDER,
            model_kwargs={
                "temperature": 0.5,
                "max_tokens": 3000,
                # remove any unsupported kwargs like citation_types
            },
            auth_type=AUTH_TYPE,
            auth_profile=OCI_PROFILE,
        )
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        raise


def test():
    # Invocation
    messages = [
        (
            "system",
            "You are a helpful assistant that translates English to French. Translate the user sentence.",
        ),
        ("human", "I love programming."),
    ]

    llm = initialize_llm()
    print(llm)
    response = llm.invoke(messages)
    print(response.content)

if __name__ == "__main__":
    test()