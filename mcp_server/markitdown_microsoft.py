#markitdown - microsoft

from mcp.server import Server, stdio, models, NotificationOptions
import mcp.types as types
from markitdown import MarkItDown
from typing import Tuple
from mcp.server.fastmcp import FastMCP
  
# Create a FastMCP server instance with the name "Math"
mcp = FastMCP("Math")

PROMPTS = {
    "md": types.Prompt(
        name="md",
        description="Convert document to markdown format using MarkItDown",
        arguments=[
            types.PromptArgument(
                name="file_path",
                description="A URI to any document or file",
                required=True,
            )
        ],
    )
}

@mcp.tool()
def convert_to_markdown(file_path: str) -> Tuple[str | None, str]:
    try:
        md = MarkItDown()
        result = md.convert(file_path)
        return result.title, result.text_content

    except Exception as e:
        return None, f"Error converting document: {str(e)}"




@app.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return list(PROMPTS.values())


@app.get_prompt()
async def get_prompt(
    name: str, arguments: dict[str, str] | None = None
) -> types.GetPromptResult:
    if name not in PROMPTS:
        raise ValueError(f"Prompt not found: {name}")

    if name == "md":
        if not arguments:
            raise ValueError("Arguments required")

        file_path = arguments.get("file_path")

        if not file_path:
            raise ValueError("file_path is required")

        try:
            markdown_title, markdown_content = convert_to_markdown(file_path)

            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=f"Here is the converted document in markdown format:\n{'' if not markdown_title else markdown_title}\n{markdown_content}",
                        ),
                    )
                ]
            )

        except Exception as e:
            raise ValueError(f"Error processing document: {str(e)}")

    raise ValueError("Prompt implementation not found")


async def run():
    async with stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            models.InitializationOptions(
                server_name="example",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )