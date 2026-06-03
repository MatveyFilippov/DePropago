from base64 import urlsafe_b64decode, urlsafe_b64encode
from cryptography.hazmat.primitives.asymmetric import x25519


def encode_call_ephemeral_public_key(call_ephemeral_public_key: bytes) -> str:
    return urlsafe_b64encode(call_ephemeral_public_key).decode("ASCII")


def decode_call_ephemeral_public_key(call_ephemeral_public_key: str) -> bytes:
    return urlsafe_b64decode(call_ephemeral_public_key.encode("ASCII"))


class CallEphemeralPublicKey:
    __slots__ = ("__raw_bytes", "__str", "__key")

    def __new__(cls, raw_bytes: bytes) -> 'CallEphemeralPublicKey':
        obj = super().__new__(cls)
        obj.__raw_bytes = raw_bytes
        obj.__str = None  # Must be set while init
        obj.__key = None  # Must be set while init
        return obj

    def __init__(self, raw_bytes: bytes):
        if self.__str is None:
            self.__str: str = encode_call_ephemeral_public_key(raw_bytes)
        if self.__key is None:
            self.__key: x25519.X25519PublicKey = x25519.X25519PublicKey.from_public_bytes(raw_bytes)

    @classmethod
    def from_str(cls, call_ephemeral_public_key_str: str) -> 'CallEphemeralPublicKey':
        call_ephemeral_public_key_raw_bytes = decode_call_ephemeral_public_key(call_ephemeral_public_key_str)

        obj = cls.__new__(cls, raw_bytes=call_ephemeral_public_key_raw_bytes)
        obj.__str = call_ephemeral_public_key_str
        obj.__key = x25519.X25519PublicKey.from_public_bytes(call_ephemeral_public_key_raw_bytes)

        return obj

    @classmethod
    def from_key(cls, call_ephemeral_public_key: x25519.X25519PublicKey) -> 'CallEphemeralPublicKey':
        call_ephemeral_public_key_raw_bytes = call_ephemeral_public_key.public_bytes_raw()

        obj = cls.__new__(cls, raw_bytes=call_ephemeral_public_key_raw_bytes)
        obj.__str = encode_call_ephemeral_public_key(call_ephemeral_public_key_raw_bytes)
        obj.__key = call_ephemeral_public_key

        return obj

    @property
    def raw_bytes(self) -> bytes:
        return self.__raw_bytes

    def __bytes__(self) -> bytes:
        return self.raw_bytes

    @property
    def str(self) -> str:
        return self.__str

    def __str__(self) -> str:
        return self.str

    @property
    def key(self) -> x25519.X25519PublicKey:
        return self.__key
