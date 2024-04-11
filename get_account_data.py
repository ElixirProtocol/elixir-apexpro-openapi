
import asyncio

from apexpro.constants import APEX_HTTP_TEST, NETWORKID_TEST, REGISTER_ENVID_TEST
from apexpro.http_private import HttpPrivate

credentials = {'key': '4a6f42cb-4bbe-3703-6af7-71a5107ef001', 'secret': 'SItVD3cPjfpNGywQCX0gVT49-Fe4pUDxtTRUa6tb', 'passphrase': 'UaCYNGR7eWihsjIKYGEQ'}

import datetime

async def setup():
    client = HttpPrivate(
        endpoint=APEX_HTTP_TEST,
        network_id=NETWORKID_TEST,
        env_id=REGISTER_ENVID_TEST,
        api_key_credentials=credentials,
    )

    account_data = await client.get_account_balance_v2()
    print("eq", account_data["data"]["usdcBalance"]["totalEquityValue"])
    print("avl bal", account_data["data"]["usdcBalance"]["availableBalance"])

    # Fetching and printing open orders
    open_orders_data = await client.open_orders_v2(token="USDC")
    open_orders = open_orders_data['data']
    if open_orders:
        print("Current Open Orders:")
        for order in open_orders:
            # Convert 'createdAt' from milliseconds to a readable date format
            created_at_timestamp = order['createdAt'] / 1000.0  # Convert ms to seconds
            created_at_date = datetime.datetime.fromtimestamp(created_at_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"Order ID: {order['id']}, Symbol: {order['symbol']}, Side: {order['side']}, Price: {order['price']}, Size: {order['size']}, Status: {order['status']}, Created At: {created_at_date}")
    else:
        print("No open orders found.")

    # Fetching and printing last filled order
    filled_orders_data = await client.fills_v2(token="USDC")
    filled_orders = filled_orders_data['data'].get('orders', [])
    last_filled_order = filled_orders[0] if filled_orders else None
    if last_filled_order:
        print("\nLast Filled Order:")
        print(f"Order ID: {last_filled_order['id']}, Symbol: {last_filled_order['symbol']}, Side: {last_filled_order['side']}, Price: {last_filled_order['price']}, Size: {last_filled_order['size']}, Created At: {datetime.datetime.fromtimestamp(last_filled_order['createdAt'] / 1000.0).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("No fill orders found.")

if __name__ == "__main__":
    asyncio.run(setup())