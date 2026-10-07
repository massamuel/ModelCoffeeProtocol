"""Deterministic MCP walkthrough; no LLM key needed. Start both servers first."""
import asyncio
import os
from dotenv import load_dotenv
from fastmcp import Client

load_dotenv()

async def main():
    async with Client(os.getenv('MCP_URL', 'http://127.0.0.1:8001/mcp')) as client:
        print('Discovered tools:', [tool.name for tool in await client.list_tools()])
        print('Inventory:', (await client.call_tool('check_inventory', {})).data)
        print('Vendors:', (await client.call_tool('list_vendors', {})).data)
        for vendor in ['roaster-a', 'roaster-b']:
            quote = (await client.call_tool('request_quote', {'vendor': vendor, 'quantity_kg': 25})).data
            result = await client.call_tool('negotiate_quote', {
                'quote_id': quote['id'], 'unit_price_cents': 2200, 'shipping_cents': 0})
            print('Negotiated quote:', result.data)
        print('Simulation complete. No orders placed.')

if __name__ == '__main__':
    asyncio.run(main())
