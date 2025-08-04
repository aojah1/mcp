### Model Context Protocol (MCP) is an open standard that enables developers to build secure, two‑way connections between their data sources and AI-powered tools, acting like a “USB‑C port” for AI models to access external context

Getting started with OCI Agents in 2 step :

### Configure your development environment
> Fork the repository
> https://github.com/aojah1/mcp
> 
> Clone the fork locally
> 
> git clone https://github.com/<your_user_name>/mcp.git

## Optional commands
    How to actually get Python 3.13 on macOS (change it for your machine)
    Option 1 : Homebrew (simplest)
    brew update
    brew install python@3.13          # puts python3.13 in /opt/homebrew/bin
    echo 'export PATH="/opt/homebrew/opt/python@3.13/bin:$PATH"' >> ~/.zshrc
    exec $SHELL                       # reload shell so python3.13 is found
    python3.13 --version              # → Python 3.13.x
    
    Option 2 : pyenv (lets you switch versions)
    brew install pyenv
    pyenv install 3.13.0
    pyenv global 3.13.0
    python --version                  # now 3.13.0

## Client Library
    cd mcp_client

## Configuring and running the agent
    python3.13 -m venv .venv_mcp
    source .venv_mcp/bin/activate

## Installing all the required packages

# After you create a project and a virtual environment, install the latest version of required packages:
    python3.13 -m pip install -r requirements.txt

## Configuring your .env (config) file
> Rename the mcp_client/config/sample_.env to mcp_client/config/.env
> Change the config variables based on your agents requirements