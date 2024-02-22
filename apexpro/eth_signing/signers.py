import eth_account

from apexpro.constants import SIGNATURE_TYPE_NO_PREPEND, SIGNATURE_TYPE_PERSONAL
from apexpro.eth_signing import util
from apexpro.eth_signing.hsm import HSMSigner


class Signer(object):

    def sign(
        self,
        eip712_message,
        message_hash,
        opt_signer_address,
    ):
        '''
        Sign an EIP-712 message.

        Returns a “typed signature” whose last byte indicates whether the hash
        was prepended before being signed.

        :param eip712_message: required
        :type eip712_message: dict

        :param message_hash: required
        :type message_hash: HexBytes

        :param opt_signer_address: optional
        :type opt_signer_address: str

        :returns: str
        '''
        raise NotImplementedError()

class SignWithHSM(Signer):
    def __init__(self, hsm_instance: HSMSigner) -> None:
        self._hsm = hsm_instance
        self.address = self._hsm.address

    async def sign(
        self,
        eip712_message, # Ignored
        message_hash,
        opt_signer_address,
    ):
        raw_signature = await self._hsm.sign(message_hash)
        ethereum_signature, _, _ = self._hsm.adjust_and_recover_signature(message_hash, raw_signature)
        typed_signature = util.create_typed_signature(
            ethereum_signature.hex(),
            SIGNATURE_TYPE_NO_PREPEND,
        )
        return typed_signature
    
    async def sign_person(
            self,
            eip712_message,  # Ignored.
            message_hash,
            opt_signer_address,
    ):
        raw_signature = await self._hsm.sign(message_hash)
        ethereum_signature, _, _ = self._hsm.adjust_and_recover_signature(message_hash, raw_signature)
        typed_signature = util.create_typed_signature(
            ethereum_signature.hex(),
            SIGNATURE_TYPE_PERSONAL,
        )
        return typed_signature

class SignWithWeb3(Signer):

    def __init__(self, web3):
        self.web3 = web3

    def sign(
        self,
        eip712_message,
        message_hash,  # Ignored.
        opt_signer_address,
    ):
        signer_address = opt_signer_address or self.web3.eth.defaultAccount
        if not signer_address:
            raise ValueError(
                'Must set ethereum_address or web3.eth.defaultAccount',
            )
        raw_signature = self.web3.eth.signTypedData(
            signer_address,
            eip712_message,
        )
        typed_signature = util.create_typed_signature(
            raw_signature.hex(),
            SIGNATURE_TYPE_NO_PREPEND,
        )
        return typed_signature


class SignWithKey(Signer):

    def __init__(self, private_key):
        self.address = eth_account.Account.from_key(private_key).address
        self._private_key = private_key

    def sign(
        self,
        eip712_message,  # Ignored.
        message_hash,
        opt_signer_address,
    ):
        if (
            opt_signer_address is not None and
            opt_signer_address != self.address
        ):
            raise ValueError(
                'signer_address is {} but Ethereum key (eth_private_key / '
                'web3_account) corresponds to address {}'.format(
                    opt_signer_address,
                    self.address,
                ),
            )
        signed_message = eth_account.Account._sign_hash(
            message_hash.hex(),
            self._private_key,
        )
        typed_signature = util.create_typed_signature(
            signed_message.signature.hex(),
            SIGNATURE_TYPE_NO_PREPEND,
        )
        return typed_signature

    def sign_person(
            self,
            eip712_message,  # Ignored.
            message_hash,
            opt_signer_address,
    ):
        if (
                opt_signer_address is not None and
                opt_signer_address != self.address
        ):
            raise ValueError(
                'signer_address is {} but Ethereum key (eth_private_key / '
                'web3_account) corresponds to address {}'.format(
                    opt_signer_address,
                    self.address,
                ),
            )

        signed_message = eth_account.Account._sign_hash(
            message_hash.hex(),
            self._private_key,
        )
        typed_signature = util.create_typed_signature(
            signed_message.signature.hex(),
            SIGNATURE_TYPE_PERSONAL,
        )
        return typed_signature
