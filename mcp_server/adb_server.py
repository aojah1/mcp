# Oracle Autonomous DB Server
# Modified to connect to ADW (Autonomous Database)

from mcp.server.fastmcp import FastMCP, Context
import json
import os
import sys
from typing import Dict, List, AsyncIterator, Optional
import time
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

from db_context import DatabaseContext

# Load environment variables from .env file
load_dotenv()

# Oracle Autonomous Connection Details
WALLET_PATH = os.getenv('WALLET_PATH')  # Path to your wallet directory
TARGET_SCHEMA = os.getenv('TARGET_SCHEMA')
CACHE_DIR = os.getenv('CACHE_DIR', '.cache')

# Autonomous service name
SERVICE_NAME = "mvdvitnosgjllaz_adwtest_medium.adb.oraclecloud.com"

# For Autonomous DB, thick mode is recommended (Oracle Client Libraries)
USE_THICK_MODE = False

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[DatabaseContext]:
    """Manage application lifecycle and ensure DatabaseContext is properly initialized"""
    print("App Lifespan initializing", file=sys.stderr)
    
    if not WALLET_PATH:
        raise ValueError("WALLET_PATH environment variable is required. Set it in .env file or environment.")

    # Setting Oracle Client Environment Variables
    os.environ['TNS_ADMIN'] = WALLET_PATH  # This allows SSL configs to be automatically picked
    connection_string = f"(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.us-ashburn-1.oraclecloud.com))(connect_data=(service_name={SERVICE_NAME}))(security=(ssl_server_dn_match=yes)))"

    cache_dir = Path(CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    db_context = DatabaseContext(
        connection_string=connection_string,
        cache_path=cache_dir / 'schema_cache.json',
        target_schema=TARGET_SCHEMA,
        use_thick_mode=USE_THICK_MODE
    )
    
    try:
        print("Initializing database cache...", file=sys.stderr)
        await db_context.initialize()
        print("Cache ready!", file=sys.stderr)
        yield db_context
    finally:
        print("Closing database connections...", file=sys.stderr)
        await db_context.close()
        print("Database connections closed", file=sys.stderr)

# Initialize FastMCP server
mcp = FastMCP("oracle", lifespan=app_lifespan)
print("FastMCP server initialized", file=sys.stderr)

# (All your tools: get_table_schema, rebuild_schema_cache, etc. remain exactly same below.)

if __name__ == "__main__":
    mcp.run(transport="stdio")