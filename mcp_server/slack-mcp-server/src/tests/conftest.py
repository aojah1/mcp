"""Pytest configuration and fixtures."""
import pytest,OS

from pathlib import Path
from dotenv import load_dotenv

# ────────────────────────────────────────────────────────
# 1) bootstrap paths + env + llm
# ────────────────────────────────────────────────────────
THIS_DIR = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parent.parent
print(PROJECT_ROOT)
load_dotenv(PROJECT_ROOT / "config/.env")  # expects OCI_ vars in .env


# Get Slack token from environment
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')


@pytest.fixture
def mock_slack_bot_token():
    """Return a mock Slack bot token."""
    return SLACK_BOT_TOKEN