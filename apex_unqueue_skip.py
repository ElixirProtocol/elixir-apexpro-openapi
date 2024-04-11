import asyncio
import json

from eth_keys.datatypes import PublicKey
from eth_account._utils.signing import to_eth_v
from eth_account._utils.legacy_transactions import encode_transaction, serializable_unsigned_transaction_from_dict
from apex_hsm import APEXHSMSession
from apex_key_setup import (ELIXIR_APEX_MANAGER_MAPPING, HSM_PIN, LIB_PATH)
from web3 import Web3
from hsm_session import HsmSession

chain_id = 11155111
HSM_LABEL = "ElixirTestPrivateKey_APEX_BTC"
RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/wiswfRL68Nkab9qGg6VA5iQWuqlposQg"

provider = Web3.HTTPProvider(RPC_URL)
provider.middlewares.clear()

async def setup():
    await HsmSession.start_session(hsm_pin=HSM_PIN, lib_path=LIB_PATH)

    public_key_raw = await HsmSession.get_public_key_raw(HSM_LABEL)
    pub_key = PublicKey(bytes(public_key_raw[3:]))
    ethereum_address = pub_key.to_checksum_address()

    hsm_instance = APEXHSMSession(
        hsm_pin=HSM_PIN,
        address=ethereum_address,
        hsm_key_label=HSM_LABEL,
        lib_path=LIB_PATH,
    )

    w3 = Web3(provider)
    contract_abi = json.load(open('./apex_mgr.abi.json'))
    apex_mgr_contract = w3.eth.contract(
        address=ELIXIR_APEX_MANAGER_MAPPING["testnet"],
        abi=contract_abi
    )

    nonce = w3.eth.get_transaction_count(ethereum_address)

    tx_data_sample_bytes = b''
    queue_id = 13

    elixir_txn = apex_mgr_contract.functions.unqueue(queue_id, tx_data_sample_bytes).build_transaction({
        'chainId': chain_id,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })

    # hash the transaction
    unsigned_transaction = serializable_unsigned_transaction_from_dict(elixir_txn)
    msghash = unsigned_transaction.hash()

    # get signature from HSM
    generic_signature = await hsm_instance.sign(msghash)
    _, _, vrs = hsm_instance.adjust_and_recover_signature(msghash, generic_signature)

    processed_v = to_eth_v(vrs[0], chain_id)

    encoded_transaction = encode_transaction(unsigned_transaction, vrs=(processed_v, vrs[1], vrs[2]))

    pre_tx_hash = w3.keccak(encoded_transaction)
    print(f"[WITHDRAWAL] sending unqueue txn. tx_hash: {pre_tx_hash.hex()}")

    tx_hash = w3.eth.send_raw_transaction(encoded_transaction)
    tx_receipt =  w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"tx receipt: {tx_receipt}")

if __name__ == "__main__":
    asyncio.run(setup())