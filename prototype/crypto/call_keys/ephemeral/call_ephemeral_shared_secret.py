from .call_ephemeral_keys import CallEphemeralKeys
from .call_ephemeral_public_key import CallEphemeralPublicKey


class CallEphemeralSharedSecret:
    __slots__ = ("__call_ephemeral_shared_secret",)

    def __init__(self, self_call_ephemeral_keys: CallEphemeralKeys, counterparty_call_ephemeral_public_key: CallEphemeralPublicKey):
        self.__call_ephemeral_shared_secret = self_call_ephemeral_keys.call_ephemeral_secret_key.exchange(counterparty_call_ephemeral_public_key.key)

    @property
    def raw_bytes(self) -> bytes:
        return self.__call_ephemeral_shared_secret

    def __bytes__(self) -> bytes:
        return self.raw_bytes
