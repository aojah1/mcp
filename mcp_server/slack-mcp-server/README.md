# Slack MCP Server

This repository contains the MCP (Model Control Protocol) code to deploy Slack Tools

## Project Structure

``` 
slack-mcp-server/
├── requirements.txt        # install dependencies
├── config
    ├── .env                # Environment variables (not tracked in git)
├── src
    ├── main.py             # Main application entry point
    ├── tools/              # Utility tools
    ├── tests/              # Test suite
    ├── utls/
        ├── utils_mcp.py    # helper functions
```

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mcp-demo
   ```

2. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Create and activate virtual environment using uv:
   ```bash
   uv venv
   source .venv/bin/activate  # On Unix/macOS
   # OR
   .venv\Scripts\activate     # On Windows
   ```

4. Install dependencies using uv:
   ```bash
   uv pip install -e .
   ```

5. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Running the Application

1. Activate the virtual environment (if not already activated):
   ```bash
   source .venv/bin/activate  # On Unix/macOS
   # OR
   .venv\Scripts\activate     # On Windows
   ```

2. Run the main application:
   ```bash
   python main.py
   ```

## Running Tests

To run the test suite:

```bash
pytest
```

## Development

This project uses:
- Python for the core implementation
- uv for dependency management and virtual environments
- pytest for testing
- pyproject.toml for project configuration

## License

[Add your license information here]
