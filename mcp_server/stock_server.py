#stocks
import appdirs as ad
ad.user_cache_dir = lambda *args: "/tmp"
import yfinance as yf
from fastmcp import FastMCP
from pandas import DataFrame

mcp_stock_server = FastMCP("stocks1")

@mcp_stock_server.tool()
def fetch_stock_info(symbol: str) -> dict:
    """Get Company's general information."""
    stock = yf.Ticker(symbol)
    return stock.info

@mcp_stock_server.tool()
def fetch_quarterly_financials(symbol: str) -> DataFrame :
    """Get stock quarterly financials."""
    stock = yf.Ticker(symbol)
    return stock.quarterly_financials.T

@mcp_stock_server.tool()
def fetch_annual_financials(symbol: str) -> DataFrame:
    """Get stock annual financials."""
    stock = yf.Ticker(symbol)
    return stock.financials.T

if __name__ == "__main__":
    mcp_stock_server.run(transport="stdio")