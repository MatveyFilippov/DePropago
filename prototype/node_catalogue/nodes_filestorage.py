from abc import ABC, abstractmethod
import lmdb
import orjson
from .node_address import NodeAddress
from ..crypto.node_keys import NodePublicKey


class NodesFileStorage(ABC):
    @abstractmethod
    def open(self, readonly: bool = True):
        ...

    @abstractmethod
    def set(self, node_public_key: NodePublicKey, node_addresses: list[NodeAddress]):
        ...

    @abstractmethod
    def get(self, node_public_key: NodePublicKey) -> list[NodeAddress]:
        ...

    @abstractmethod
    def items(self) -> dict[NodePublicKey, list[NodeAddress]]:
        ...

    @abstractmethod
    def remove(self, node_public_key: NodePublicKey):
        ...

    @abstractmethod
    def close(self):
        ...


class NodesFileStorageLMDB(NodesFileStorage):
    SIZE = 5*1024*1024*1024  # 5GB just for prototype

    class __KeySerializer:
        @classmethod
        def node_public_key_to_key_bytes(cls, node_public_key: NodePublicKey) -> bytes:
            return node_public_key.raw_bytes

        @classmethod
        def key_bytes_to_node_public_key(cls, key_bytes: bytes) -> NodePublicKey:
            return NodePublicKey(raw_bytes=key_bytes)

    class __ValueSerializer:
        class NodeAddressDictKeys:
            IP = "i"
            PORT = "p"
            TIMESTAMP = "t"
            SIGNATURE = "s"

        @classmethod
        def _node_address_to_dict(cls, node_address: NodeAddress) -> dict[str, str | int]:
            return {
                cls.NodeAddressDictKeys.IP: node_address.ip,
                cls.NodeAddressDictKeys.PORT: node_address.port,
                cls.NodeAddressDictKeys.TIMESTAMP: node_address.creation_timestamp,
                cls.NodeAddressDictKeys.SIGNATURE: node_address.origin_message_signature,
            }

        @classmethod
        def _dict_to_node_address(cls, node_address_dict: dict[str, str | int]) -> NodeAddress:
            return NodeAddress(
                ip=node_address_dict[cls.NodeAddressDictKeys.IP],
                port=node_address_dict[cls.NodeAddressDictKeys.PORT],
                timestamp=node_address_dict[cls.NodeAddressDictKeys.TIMESTAMP],
                origin_message_signature=node_address_dict[cls.NodeAddressDictKeys.SIGNATURE],
            )

        @classmethod
        def node_addresses_list_to_bytes_value(cls, node_addresses: list[NodeAddress]) -> bytes:
            list_of_dict_node_addresses: list[dict[str, str | int]] = [
                cls._node_address_to_dict(node_address) for node_address in node_addresses
            ]
            return orjson.dumps(list_of_dict_node_addresses)

        @classmethod
        def bytes_value_to_node_addresses_list(cls, bytes_value: bytes) -> list[NodeAddress]:
            list_of_dict_node_addresses: list[dict[str, str | int]] = orjson.loads(bytes_value)
            return [
                cls._dict_to_node_address(node_address_dict) for node_address_dict in list_of_dict_node_addresses
            ]

    def __init__(self, dir_path: str):
        self.__dir_path: str = dir_path
        self._env: lmdb.Environment | None = None

    def open(self, readonly: bool = True):
        if self._env is not None:
            raise ValueError("File is already open")
        self._env = lmdb.open(
            path=self.__dir_path,
            map_size=self.SIZE,
            max_dbs=1,
            readonly=readonly,
            sync=True,  # Ignore while readonly
            metasync=True,  # Ignore while readonly
            writemap=False,  # Ignore while readonly
            map_async=True,  # Ignore while readonly
            meminit=(not readonly),
            lock=(not readonly),
        )

    def set(self, node_public_key: NodePublicKey, node_addresses: list[NodeAddress]):
        with self._env.begin(write=True) as transaction:
            transaction.put(
                key=self.__KeySerializer.node_public_key_to_key_bytes(node_public_key),
                value=self.__ValueSerializer.node_addresses_list_to_bytes_value(node_addresses),
                overwrite=True,
                dupdata=False,
            )

    def get(self, node_public_key: NodePublicKey) -> list[NodeAddress]:
        with self._env.begin(write=False, buffers=False) as transaction:
            value = transaction.get(key=self.__KeySerializer.node_public_key_to_key_bytes(node_public_key))
            if not value:
                raise KeyError(f"No such key '{node_public_key}' in file")
            return self.__ValueSerializer.bytes_value_to_node_addresses_list(value)

    def items(self) -> dict[NodePublicKey, list[NodeAddress]]:
        with self._env.begin(write=False, buffers=False) as transaction:
            cursor = transaction.cursor()
            return {
                self.__KeySerializer.key_bytes_to_node_public_key(key): self.__ValueSerializer.bytes_value_to_node_addresses_list(value)
                for key, value in cursor
            }

    def remove(self, node_public_key: NodePublicKey):
        with self._env.begin(write=True) as transaction:
            transaction.delete(key=self.__KeySerializer.node_public_key_to_key_bytes(node_public_key))

    def close(self):
        if self._env is not None:
            self._env.close()
            self._env = None
