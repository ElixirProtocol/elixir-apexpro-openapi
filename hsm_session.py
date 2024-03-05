import asyncio
import logging

from PyKCS11 import PyKCS11


class HsmSession:
    __pkcs11 = PyKCS11.PyKCS11Lib()
    _session = None
    _lock = asyncio.Lock()
    _session_ready = asyncio.Event()

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("This class cannot be instantiated")

    @classmethod
    async def start_session(cls, hsm_pin: str, lib_path: str = "/opt/cloudhsm/lib/libcloudhsm_pkcs11.so"):
        async with cls._lock:
            if cls._session is not None:
                return

            try:
                cls.__pkcs11.load(lib_path)
                slot = cls.__pkcs11.getSlotList()[0]
                cls._session = cls.__pkcs11.openSession(
                    slot, PyKCS11.CKF_RW_SESSION | PyKCS11.CKF_SERIAL_SESSION
                )
                cls._session.login(hsm_pin)
                cls._session_ready.set()
                logging.info("[HSM] PKCS11: Logged in.")
            except Exception as e:
                cls._session = None
                logging.error(f"[HSM] PKCS11 Error when creating session. error={e}")
                raise

    @classmethod
    async def close_session(cls):
        async with cls._lock:
            if cls._session is None:
                return

            try:
                cls._session.logout()
            except Exception as e:
                logging.error(f"[HSM] PKCS11 Error when logging out session. error={e}")
            finally:
                cls._session.closeSession()
                cls._session = None
                cls._session_ready.clear()

    @classmethod
    async def get_session(cls):
        await cls._session_ready.wait()  # Wait until the session is ready
        return cls._session
