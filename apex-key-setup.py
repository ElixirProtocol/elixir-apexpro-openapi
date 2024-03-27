import argparse
import asyncio
from eth_keys.datatypes import PublicKey
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
HSM_PIN = "user:$^94o7u!5qGKIAt&MrON@jq1o$QeaSUe"
LIB_PATH = "/opt/cloudhsm/lib/libcloudhsm_pkcs11.so"

async def setup(stark_private_key=None, use_hsm=False, ethereum_private_key=None, hsm_label=None):
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
        token="USDC",
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

    print(f"Ethereum Address: {hsm_instance.address if use_hsm else client.default_address}")

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
    parser.add_argument(
        "--hsm-label", type=str, help="Label of the HSM key in the HSM", required=True
    )

    args = parser.parse_args()

    if args.use_hsm:
        asyncio.run(setup(
            stark_private_key=args.stark_private_key,
            use_hsm=True,
            hsm_label=args.hsm_label)
        )
    elif args.eth_private_key:
        asyncio.run(
            setup(
                ethereum_private_key=args.eth_private_key,
                stark_private_key=args.stark_private_key
            )
        )
    else:
        parser.error("Either --use-hsm or --eth-private-key must be provided")
