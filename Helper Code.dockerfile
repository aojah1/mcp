# Helper Code

ssh -i ssh-key-2025-01-11.key opc@132.145.166.190
ssh -i ssh-key-2025-01-11.key ubuntu@150.136.30.90:

scp -i ssh-key-2025-01-11.key \
    ~/Documents/GenAI-CoE/Agentic-Framework/source-code/MCP/langraph-mcp/mcp_client/mcp_chat_client.py \
    ubuntu@150.136.30.90:/home/ubuntu/mcp/openai-playground/mcp-agent/

    scp -r -i ssh-key-2025-01-11.key \
    ~/Documents/GenAI-CoE/Agentic-Framework/source-code/MCP/oci-langraph-mcp \
    ubuntu@150.136.30.90:/home/ubuntu/mcp/  

    