import argparse
import asyncio
from apexpro.http_private import HttpPrivate
from apexpro.constants import (
    APEX_HTTP_TEST,
    NETWORKID_TEST,
    APEX_HTTP_MAIN,
    NETWORKID_MAIN,
    REGISTER_ENVID_TEST,
)
from apexpro.starkex.helpers import private_key_to_public_key_pair_hex

from hsm_session import HsmSession
from apex_hsm import APEXHSMSession

# HSM constants
HSM_PIN = ""
HSM_ADDRESS = ""
HSM_KEY_LABEL = ""
LIB_PATH = ""


async def setup(stark_private_key=None, use_hsm=False, ethereum_private_key=None):
    if use_hsm:
        await HsmSession.start_session(hsm_pin=HSM_PIN, lib_path=LIB_PATH)

        hsm_instance = APEXHSMSession(
            hsm_pin=HSM_PIN,
            address=HSM_ADDRESS,
            hsm_key_label=HSM_KEY_LABEL,
            lib_path=LIB_PATH,
        )

        client = HttpPrivate(
            APEX_HTTP_TEST,
            network_id=NETWORKID_TEST,
            env_id=REGISTER_ENVID_TEST,
            hsm_instance=hsm_instance,
        )
    elif ethereum_private_key is not None:
        client = HttpPrivate(
            APEX_HTTP_TEST,
            network_id=NETWORKID_TEST,
            env_id=REGISTER_ENVID_TEST,
            eth_private_key=ethereum_private_key,
        )
    else:
        raise ValueError(
            "using HSM or Ethereum plain key is required."
        )
    
    if (use_hsm or ethereum_private_key) and stark_private_key is None:
        stark_key_pair = await client.derive_stark_key(client.default_address)
    else:
        stark_public_key, stark_public_key_y_coordinate = (
            private_key_to_public_key_pair_hex(stark_private_key)
        )
        stark_key_pair = {
            "public_key": stark_public_key,
            "public_key_y_coordinate": stark_public_key_y_coordinate,
            "private_key": stark_private_key,
        }

    nonceRes = await client.generate_nonce(
        starkKey=stark_key_pair["public_key"],
        ethAddress=client.default_address,
        chainId=NETWORKID_TEST,
    )

    regRes = await client.register_user_v2(
        token="USDT",
        nonce=nonceRes["data"]["nonce"],
        starkKey=stark_key_pair["public_key"],
        stark_public_key_y_coordinate=stark_key_pair["public_key_y_coordinate"],
        ethereum_address=client.default_address,
    )

    if "data" not in regRes:
        print("Failed to register user.")
        print(regRes)
        return

    key = regRes["data"]["apiKey"]["key"]
    secret = regRes["data"]["apiKey"]["secret"]
    passphrase = regRes["data"]["apiKey"]["passphrase"]

    client.api_key_credentials = {
        "key": key,
        "secret": secret,
        "passphrase": passphrase,
    }

    print("STARK Key Pair:")
    print(stark_key_pair)

    print("\nAPI Key Credentials:")
    print(client.api_key_credentials)

    print("\nAccount Position ID:")
    print(regRes["data"]["account"]["positionId"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Derive STARK keys and register user.")
    parser.add_argument("--use-hsm", action="store_true", help="Use HSM to sign")
    parser.add_argument(
        "--stark-private-key", type=str, help="Pre-calculated STARK private key"
    )
    parser.add_argument(
        "--eth-private-key", type=str, help="Plain ETH private key to sign"
    )

    args = parser.parse_args()

    if args.use_hsm:
        asyncio.run(setup(stark_private_key=args.stark_private_key, use_hsm=True))
    elif args.eth_private_key:
        asyncio.run(
            setup(
                ethereum_private_key=args.eth_private_key,
                stark_private_key=args.stark_private_key,
            )
        )
    else:
        parser.error("Either --use-hsm or --eth-private-key must be provided")
