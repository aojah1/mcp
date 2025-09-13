import sys
# from src.common.server import mcp
from src.common.config import *


# class OracleDBToolsMCPServer:
#     def __init__(self):
#         print("Starting the OracleDBToolsMCPServer", file=sys.stderr)

#     def run(self):
#         mcp.run(transport=MCP_TRANSPORT)

# @mcp.tool()
# async def ping() -> str:
#     return "pong"

# if __name__ == "__main__":
#    server = OracleDBToolsMCPServer()
#    server.run()

# server.py
# # src/main.py
# import uvicorn
# from mcp.server.fastmcp import FastMCP
# from mcp.server.streamable_http import create_streamable_http_app

# mcp = FastMCP("dbtools")

# @mcp.tool()
# async def ping() -> str:
#     return "pong"

# app = create_streamable_http_app(mcp)   # wires GET/POST /mcp with SSE + session id

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8001)

import uvicorn
#from mcp.server.fastmcp import FastMCP

#mcp = FastMCP("dbtools")  # add lifespan/auth/stateless_http as needed
from src.common.server import mcp
import src.tools

class OracleDBToolsMCPServer:
    def __init__(self):
        print("Starting the OracleDBToolsMCPServer", file=sys.stderr)

    def run(self):
        # Build an ASGI app that serves the Streamable HTTP transport.
        # By default this app handles /mcp inside itself.
        app = mcp.streamable_http_app()
        # Run the ASGI app directly
        uvicorn.run(app, host="0.0.0.0", port=8001)

@mcp.tool()
def ping() -> str:
    """Health check."""
    return "pong11"



if __name__ == "__main__":
    server = OracleDBToolsMCPServer()
    server.run()   

