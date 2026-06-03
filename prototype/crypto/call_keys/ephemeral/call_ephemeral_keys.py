from cryptography.hazmat.primitives.asymmetric import x25519
from .call_ephemeral_public_key import CallEphemeralPublicKey


class CallEphemeralKeys:
    __slots__ = ("__call_ephemeral_secret_key", "__call_ephemeral_public_key")

    def __init__(self, call_ephemeral_secret_key: x25519.X25519PrivateKey):
        self.__call_ephemeral_secret_key: x25519.X25519PrivateKey = call_ephemeral_secret_key
        self.__call_ephemeral_public_key: CallEphemeralPublicKey = CallEphemeralPublicKey.from_key(
            call_ephemeral_public_key=call_ephemeral_secret_key.public_key(),
        )

    @property
    def call_ephemeral_secret_key(self) -> x25519.X25519PrivateKey:
        return self.__call_ephemeral_secret_key

    @property
    def call_ephemeral_public_key(self) -> CallEphemeralPublicKey:
        return self.__call_ephemeral_public_key

    @classmethod
    def generate(cls) -> 'CallEphemeralKeys':
        call_ephemeral_secret_key = x25519.X25519PrivateKey.generate()
        return cls(call_ephemeral_secret_key=call_ephemeral_secret_key)
