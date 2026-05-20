from cryptography.hazmat.primitives.asymmetric import ed25519
from .node_public_key import NodePublicKey
from .node_seed_phrase import NodeSeedPhrase


NODE_SECRET_KEY_SEED_BYTES = 32


class NodeKeys:
    __slots__ = ("__node_secret_key", "__node_public_key")

    def __init__(self, node_secret_key: ed25519.Ed25519PrivateKey):
        self.__node_secret_key: ed25519.Ed25519PrivateKey = node_secret_key
        self.__node_public_key: NodePublicKey = NodePublicKey.from_key(node_public_key=node_secret_key.public_key())

    @property
    def node_secret_key(self) -> ed25519.Ed25519PrivateKey:
        return self.__node_secret_key

    @property
    def node_public_key(self) -> NodePublicKey:
        return self.__node_public_key

    @classmethod
    def from_node_seed_phrase(cls, node_seed_phrase: NodeSeedPhrase) -> 'NodeKeys':
        node_master_seed = node_seed_phrase.to_node_master_seed()
        node_secret_key_seed = node_master_seed[:NODE_SECRET_KEY_SEED_BYTES]
        node_secret_key = ed25519.Ed25519PrivateKey.from_private_bytes(node_secret_key_seed)
        return cls(node_secret_key=node_secret_key)
