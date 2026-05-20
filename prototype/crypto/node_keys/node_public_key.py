from base64 import urlsafe_b64decode, urlsafe_b64encode
from cryptography.hazmat.primitives.asymmetric import ed25519


class CacheLRU:
    FIFO_SIZE = 256
    __cache: dict[bytes, 'NodePublicKey'] = {}

    @classmethod
    def is_exists(cls, raw_bytes: bytes) -> bool:
        return raw_bytes in cls.__cache

    @classmethod
    def get(cls, raw_bytes: bytes) -> 'NodePublicKey':
        return cls.__cache[raw_bytes]

    @classmethod
    def put(cls, raw_bytes: bytes, obj: 'NodePublicKey'):
        cls.__cache[raw_bytes] = obj
        if len(cls.__cache) > cls.FIFO_SIZE:
            cls.__cache.pop(next(iter(cls.__cache)))


def encode_node_public_key(node_public_key: bytes) -> str:
    return urlsafe_b64encode(node_public_key).decode("ASCII")


def decode_node_public_key(node_public_key: str) -> bytes:
    return urlsafe_b64decode(node_public_key.encode("ASCII"))


class NodePublicKey:
    __slots__ = ("__raw_bytes", "__hash", "__str", "__key")

    def __new__(cls, raw_bytes: bytes) -> 'NodePublicKey':
        if CacheLRU.is_exists(raw_bytes):
            return CacheLRU.get(raw_bytes)

        obj = super().__new__(cls)
        obj.__raw_bytes = raw_bytes
        obj.__hash = hash(raw_bytes)
        obj.__str = None  # Must be set while init
        obj.__key = None  # Must be set while init

        CacheLRU.put(raw_bytes, obj)

        return obj

    def __init__(self, raw_bytes: bytes):
        if self.__str is None:
            self.__str: str = encode_node_public_key(raw_bytes)
        if self.__key is None:
            self.__key: ed25519.Ed25519PublicKey = ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)

    @classmethod
    def from_str(cls, node_public_key_str: str) -> 'NodePublicKey':
        node_public_key_raw_bytes = decode_node_public_key(node_public_key_str)

        if CacheLRU.is_exists(node_public_key_raw_bytes):
            return CacheLRU.get(node_public_key_raw_bytes)

        obj = cls.__new__(cls, raw_bytes=node_public_key_raw_bytes)
        obj.__str = node_public_key_str
        obj.__key = ed25519.Ed25519PublicKey.from_public_bytes(node_public_key_raw_bytes)

        return obj

    @classmethod
    def from_key(cls, node_public_key: ed25519.Ed25519PublicKey) -> 'NodePublicKey':
        node_public_key_raw_bytes = node_public_key.public_bytes_raw()

        if CacheLRU.is_exists(node_public_key_raw_bytes):
            return CacheLRU.get(node_public_key_raw_bytes)

        obj = cls.__new__(cls, raw_bytes=node_public_key_raw_bytes)
        obj.__str = encode_node_public_key(node_public_key_raw_bytes)
        obj.__key = node_public_key

        return obj

    def __eq__(self, other) -> bool:
        if isinstance(other, NodePublicKey):
            return self.__raw_bytes == other.__raw_bytes
        return NotImplemented

    def __hash__(self) -> int:
        return self.__hash

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
    def key(self) -> ed25519.Ed25519PublicKey:
        return self.__key
