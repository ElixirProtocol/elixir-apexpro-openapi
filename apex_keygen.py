import asyncio
import json
from apex_key_setup import generate_credentials

coins = ["BTC", "ETH", "AVAX", "1000PEPE", "ARB", "XRP", "ATOM", "DOGE", "MATIC", "OP", "SOL", "BNB", "LTC", "APT", "LDO", "BLUR", "BCH", "WLD", "LINK", "LBR", "TON", "DYDX", "TIA"]
network = "mainnet"

async def generate_all_credentials():
    credentials_dict = {}
    for coin in coins:
        hsm_label = f"ElixirMainnetPrivateKey_APEX_{coin}"
        credentials = await generate_credentials(
            use_hsm=True,
            hsm_label=hsm_label,
            network=network
        )
        credentials_dict[hsm_label] = credentials

    with open('credentials.json', 'w') as f:
        json.dump(credentials_dict, f, indent=4)

if __name__ == "__main__":
    asyncio.run(generate_all_credentials())
