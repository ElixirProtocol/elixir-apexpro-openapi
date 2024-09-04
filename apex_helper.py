
import asyncio
from decimal import Decimal
import time

from apexpro.constants import APEX_HTTP_MAIN, NETWORKID_MAIN, REGISTER_ENVID_MAIN
from apexpro.http_private import HttpPrivate
from apexpro.http_private_stark_key_sign import HttpPrivateStark
from hsm_session import HsmSession
from apex_hsm import APEXHSMSession

credentials = {}

import datetime

# HSM constants
HSM_PIN = ""
LIB_PATH = "/opt/cloudhsm/lib/libcloudhsm_pkcs11.so"

async def setup():
    await HsmSession.start_session(hsm_pin=HSM_PIN, lib_path=LIB_PATH)
    hsm_instance = APEXHSMSession(
        hsm_pin=HSM_PIN,
        address="0x5211B69EFbBf05B154a74fd9e9cc325da1E53f4f",
        hsm_key_label="",
        lib_path=LIB_PATH,
    )

    client = HttpPrivateStark(
        endpoint=APEX_HTTP_MAIN,
        network_id=NETWORKID_MAIN,
        env_id=REGISTER_ENVID_MAIN,
        api_key_credentials=credentials,
        hsm_instance=hsm_instance,
        stark_private_key="",
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
            
            print(f"Order ID: {order['id']}, Symbol: {order['symbol']}, Type: {order['type']}, Side: {order['side']}, Price: {order['price']}, Size: {order['size']}, Status: {order['status']}, Created At: {created_at_date}")
    else:
        print("No open orders found.")

    account_data_v2 = await client.get_account_v2()
    account_positions = account_data_v2["data"]["positions"] or []
    print(account_positions)

    # cancel all
    # cancel_result = await client.delete_open_orders_v2(symbol="TIA-USDC", token="USDC")
    # print(f"Cancellation result: {cancel_result}")

    # market LONG order
    # await client.configs_v2()
    # token_data = [account for account in account_data_v2["data"]["accounts"] if account["token"] == "USDC"][0]
    # taker_fee_rate = Decimal(token_data["takerFeeRate"])
    # account_id = account_data_v2["data"]["positionId"]

    # order_result = await client.create_order_v2(
    #     symbol="TIA-USDC",
    #     side='BUY',
    #     type='MARKET',
    #     size=Decimal("24.3"),
    #     price="4.2080",
    #     accountId=account_id,
    #     timeInForce="GOOD_TIL_CANCEL",
    #     expirationEpochSeconds=time.time(),
    #     clientId="ELIXIR_MANUAL_ORDER_5",
    #     limitFeeRate=taker_fee_rate,
    # )

    # print(f"Order result: {order_result}")

    # Fetching and printing last filled order
    filled_orders_data = await client.fills_v2(token="USDC")
    filled_orders = filled_orders_data['data'].get('orders', [])
    last_filled_order = filled_orders[0] if filled_orders else None
    if last_filled_order:
        print("\nLast Filled Order:")
        print(f"Order ID: {last_filled_order['id']}, Symbol: {last_filled_order['symbol']}, Side: {last_filled_order['side']}, Price: {last_filled_order['price']}, Size: {last_filled_order['size']}, Created At: {datetime.datetime.fromtimestamp(last_filled_order['createdAt'] / 1000.0).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("No fill orders found.")

    # history = await client.transfers_v2(**{"limit": 100, "page": 0, "currencyId": "USDC"})
    # print("\nTransfer History:")
    # print(history)

    print(client.endpoint)
    print(client.network_id)
    print(client.env_id)

    # snapshot_data = await client.depth(symbol="BTC-USDC")


if __name__ == "__main__":
    asyncio.run(setup())