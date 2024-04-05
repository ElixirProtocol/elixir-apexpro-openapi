import argparse
import asyncio
from eth_keys.datatypes import PublicKey
from apexpro.http_private import HttpPrivate
from apexpro.constants import (
    APEX_HTTP_TEST,
    NETWORKID_TEST,
    APEX_HTTP_MAIN,
    NETWORKID_MAIN,
    REGISTER_ENVID_MAIN,
    REGISTER_ENVID_TEST,
)
from apexpro.starkex.helpers import private_key_to_public_key_pair_hex

from hsm_session import HsmSession
from apex_hsm import APEXHSMSession

# HSM constants
HSM_PIN = "user:$^94o7u!5qGKIAt&MrON@jq1o$QeaSUe"
LIB_PATH = "/opt/cloudhsm/lib/libcloudhsm_pkcs11.so"

ELIXIR_APEX_MANAGER_MAPPING = {
    "mainnet": "0xFf80F9F210c75199491bcFb086fed78AA5af87b2",
    "testnet": "0xFf80F9F210c75199491bcFb086fed78AA5af87b2",
}

NETWORK_MAPPING = {
    "mainnet": {
        "endpoint": APEX_HTTP_MAIN,
        "networkId": NETWORKID_MAIN,
        "envId": REGISTER_ENVID_MAIN
    },
    "testnet": {
        "endpoint": APEX_HTTP_TEST,
        "networkId": NETWORKID_TEST,
        "envId": REGISTER_ENVID_TEST
    }
}

async def generate_credentials(
        stark_private_key=None,
        use_hsm=False,
        ethereum_private_key=None,
        hsm_label=None,
        network="testnet",
    ):
    network_id = NETWORK_MAPPING[network]["networkId"]
    env_id = NETWORK_MAPPING[network]["envId"]
    endpoint = NETWORK_MAPPING[network]["endpoint"]

    if use_hsm:
        await HsmSession.start_session(hsm_pin=HSM_PIN, lib_path=LIB_PATH)

        public_key_raw = await HsmSession.get_public_key_raw(hsm_label)
        pub_key = PublicKey(bytes(public_key_raw[3:]))

        ethereum_address = pub_key.to_checksum_address()

        hsm_instance = APEXHSMSession(
            hsm_pin=HSM_PIN,
            address=ethereum_address,
            hsm_key_label=hsm_label,
            lib_path=LIB_PATH,
        )

        client = HttpPrivate(
            endpoint=endpoint,
            network_id=network_id,
            env_id=env_id,
            hsm_instance=hsm_instance,
        )
    elif ethereum_private_key is not None:
        client = HttpPrivate(
            endpoint=endpoint,
            network_id=network_id,
            env_id=env_id,
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
        chainId=network_id,
    )

    regRes = await client.register_user_v2(
        token="USDC",
        nonce=nonceRes["data"]["nonce"],
        starkKey=stark_key_pair["public_key"],
        stark_public_key_y_coordinate=stark_key_pair["public_key_y_coordinate"],
        ethereum_address=client.default_address,
        eth_mul_address=ELIXIR_APEX_MANAGER_MAPPING[network],
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

    print(f"Ethereum Address: {hsm_instance.address if use_hsm else client.default_address}")

    print("STARK Key Pair:")
    print(stark_key_pair)

    print("\nAPI Key Credentials:")
    print(client.api_key_credentials)

    print("\nAccount Position ID:")
    print(regRes["data"]["account"]["positionId"])

    return {
        "ethereum_address": hsm_instance.address if use_hsm else client.default_address,
        "stark_key_pair": stark_key_pair,
        "api_key_credentials": client.api_key_credentials,
        "account_position_id": regRes["data"]["account"]["positionId"],
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Derive STARK keys and register user.")
    parser.add_argument("--use-hsm", action="store_true", help="Use HSM to sign")
    parser.add_argument(
        "--stark-private-key", type=str, help="Pre-calculated STARK private key"
    )
    parser.add_argument(
        "--eth-private-key", type=str, help="Plain ETH private key to sign"
    )
    parser.add_argument(
        "--hsm-label", type=str, help="Label of the HSM key in the HSM", required=True
    )

    parser.add_argument(
        "--network", type=str, default="testnet", help="Network ID", required=True, choices=["testnet", "mainnet"]
    )

    args = parser.parse_args()

    if args.use_hsm:
        asyncio.run(
            generate_credentials(
                stark_private_key=args.stark_private_key,
                use_hsm=True,
                hsm_label=args.hsm_label,
                network=args.network
            )
        )
    elif args.eth_private_key:
        asyncio.run(
            generate_credentials(
                ethereum_private_key=args.eth_private_key,
                stark_private_key=args.stark_private_key,
                network=args.network
            )
        )
    else:
        parser.error("Either --use-hsm or --eth-private-key must be provided")
