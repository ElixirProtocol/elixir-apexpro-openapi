import logging

from eth_account._utils.signing import to_standard_v
from eth_keys import keys
from PyKCS11 import PyKCS11

from hsm_session import HsmSession
from apexpro.constants import NETWORKID_TEST


class APEXHSMSession:
    _logger = None

    def __init__(self, hsm_pin, address, hsm_key_label, lib_path="/opt/cloudhsm/lib/libcloudhsm_pkcs11.so"):
        self.hsm_pin = hsm_pin
        self.address = address
        self.lib_path = lib_path
        self.hsm_key_label = hsm_key_label

    @classmethod
    def logger(cls):
        if cls._logger is None:
            cls._logger = logging.getLogger("test")
        return cls._logger

    @property
    def ready(self):
        return all(attr is not None and attr != "" for attr in [self.hsm_key_label, self.hsm_pin, self.lib_path])

    async def sign(self, msghash, retries=3):
        if retries == 0:
            self.logger().info("[HSM] Maximum retries reached.")
            return None
        try:
            private_key_template = [
                (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
                (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_ECDSA),
                (PyKCS11.CKA_LABEL, self.hsm_key_label),
            ]
            session = await HsmSession.get_session()
            private_key = session.findObjects(private_key_template)[0]
            return session.sign(private_key, msghash, PyKCS11.Mechanism(PyKCS11.CKM_ECDSA, None))
        except PyKCS11.PyKCS11Error as e:
            self.logger().info(f"[HSM] Restarting session and retrying. error: {e}")
            await HsmSession.close_session()
            await HsmSession.start_session(self.hsm_pin, self.lib_path)
            return await self.sign(msghash, retries - 1)
        except Exception as e:
            self.logger().info(f"[HSM] Unexpected error: {e}")

    def adjust_and_recover_signature(self, msghash, signature):
        # Constants for the secp256k1 curve
        secp256k1_n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # noqa: documentation
        secp256k1_halfn = secp256k1_n // 2

        signature = bytes(signature)
        r = int.from_bytes(signature[:32], "big")
        s = int.from_bytes(signature[32:], "big")

        # Adjust s if it's greater than half of the curve order
        if s > secp256k1_halfn:
            s = secp256k1_n - s

        v_lower = NETWORKID_TEST * 2 + 35
        v_range = [v_lower, v_lower + 1]

        for v in v_range:
            v_standard = to_standard_v(v)
            signature_obj = keys.Signature(vrs=(v_standard, r, s))

            # Recover the public key from the signature
            recovered_pub_key = signature_obj.recover_public_key_from_msg_hash(msghash)
            recovered_eth_address = recovered_pub_key.to_checksum_address()

            if recovered_eth_address.lower() == self.address.lower():
                break

        # Ethereum compatible signature
        ethereum_signature = signature_obj.to_bytes()
        return ethereum_signature, recovered_eth_address, signature_obj.vrs
