import asyncio
import threading
import time

from apexpro.constants import APEX_WS_MAIN
from apexpro.websocket_api import WebSocket

api_key_credentials = {
    "key": "4e40cdfc-053e-3bcd-4584-24988a442c9f",
    "secret": "9Wa9zlBiZ3IVvFdrCVvjwhY0RK-lW1homSKCHGjv",
    "passphrase": "IjHXAzDVmCJebFdS0l3Y"
}

async def _process_order_book_event(message):
    # Process the message
    print(message)

async def _process_market_data_event(message):
    # Process the message
    print(message)

async def _process_trades_event(message):
    # Process the message
    print(message)

async def _process_account_updates(message):
    # Process the message
    print(message)
    raise Exception("LOL")

def subscribe_to_public_events(ws_client, trading_pair: str):
    ws_client.depth_stream(_process_order_book_event, trading_pair, 25)
    ws_client.ticker_stream(_process_market_data_event, trading_pair)
    ws_client.trade_stream(_process_trades_event, trading_pair)

def subscribe_to_private_events(ws_client):
    ws_client.account_info_stream_v2(_process_account_updates)

# Stress test function
def stress_test():
    starting_thread_count = threading.active_count()
    
    # Simulate a large number of public and private subscriptions
    for i in range(1):  # Adjust the range for your stress test needs
        print("Creating websocket...")
        ws_client = WebSocket(
            endpoint=APEX_WS_MAIN,
            api_key_credentials=api_key_credentials,
            event_loop=asyncio.get_event_loop(),
        )

        print("Subscribing to public events...")
        subscribe_to_public_events(ws_client, 'BTCUSDC')
        # print("Subscribing to private events...")
        # subscribe_to_private_events(ws_client)

        # Optional: sleep between iterations to simulate more realistic usage
        time.sleep(1)

        # print("Closing websocket...")
        # ws_client.close()

    while True:
        time.sleep(1)

    ending_thread_count = threading.active_count()
    
    print(f"Started with {starting_thread_count} threads.")
    print(f"Ended with {ending_thread_count} threads.")
    print(f"Created {ending_thread_count - starting_thread_count} new threads.")

# Run the stress test
stress_test()