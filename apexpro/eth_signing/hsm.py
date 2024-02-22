from abc import ABC, abstractmethod, abstractproperty
from ast import Tuple
from typing import Optional

class HSMSigner(ABC):
    @abstractproperty
    def address(self) -> str:
        """
        The address property should return the address associated with the HSM signer.

        :return: The address as a string.
        """
        pass
    @abstractmethod
    async def sign(self, msghash: bytes, retries: int = 3) -> Optional[bytes]:
        """
        Sign a message hash using the HSM.

        :param msghash: The hash of the message to be signed.
        :param retries: Number of retries for the signing operation.
        :return: The signature as bytes if successful, None otherwise.
        """
        pass

    @abstractmethod
    def adjust_and_recover_signature(self, msghash: bytes, signature: bytes) -> Tuple:
        """
        Adjusts and recovers the signature to ensure it is in the correct format and recover the signer address.

        :param msghash: The message hash that was signed.
        :param signature: The raw signature bytes.
        :return: A tuple containing the adjusted signature, the recovered address, and the signature components (v, r, s).
        """
        pass
