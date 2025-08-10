"""Main MCP server application."""

import sys, os

#print(sys.path)

# Add the src directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.tools.slack_tools import (
    list_slack_channels,
    send_slack_message,
    get_channel_messages,
)
from src.tools.config import logger

# ────────────────────────────────────────────────────────
# 1) bootstrap paths + env + llm
# ────────────────────────────────────────────────────────
THIS_DIR = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parent.parent
print(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / "config/.env")  # expects OCI_ vars in .env


# Get Slack token from environment
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN environment variable is required")

# Initialize FastMCP server
mcp = FastMCP("mcp_demo")


@mcp.tool()
async def slack_list_channels(limit: int = 100) -> str:
    """List all channels in the Slack workspace.

    Args:
        limit: Maximum number of channels to return (default 100, max 1000)
    """
    return await list_slack_channels(SLACK_BOT_TOKEN, limit)


@mcp.tool()
async def slack_send_message(channel_id: str, text: str) -> str:
    """Send a message to a Slack channel.

    Args:
        channel_id: The ID of the channel to send the message to
        text: The message text to send
    """
    return await send_slack_message(SLACK_BOT_TOKEN, channel_id, text)


@mcp.tool()
async def slack_get_messages(channel_id: str, limit: int = 50) -> str:
    """Get recent messages from a Slack channel.

    Args:
        channel_id: The ID of the channel to get messages from
        limit: Maximum number of messages to return (default 50, max 1000)
    """
    return await get_channel_messages(SLACK_BOT_TOKEN, channel_id, limit)


@mcp.tool()
async def weather_get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    return await get_alerts(state)


@mcp.tool()
async def weather_get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    return await get_forecast(latitude, longitude)


if __name__ == "__main__":
    # Initialize and run the server
    logger.info("Starting FastMCP server...")
    mcp.run(transport='stdio')