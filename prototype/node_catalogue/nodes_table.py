import random
from typing import Iterator
from .node_address import NodeAddress
from .nodes_filestorage import NodesFileStorage
from ..crypto.node_keys import NodePublicKey


NODE_ADDRESSES_QTY = 4


class NodesTable:
    __slots__ = ("__filestorage", "__cache", "__cache_node_public_keys")

    def __init__(self, based_on: NodesFileStorage):
        based_on.open(readonly=True)
        self.__cache: dict[NodePublicKey, list[NodeAddress]] = based_on.items()
        self.__cache_node_public_keys: list[NodePublicKey] = list(self.__cache.keys())
        based_on.close()

        self.__filestorage: NodesFileStorage = based_on
        self.__filestorage.open(readonly=False)

    def get_size(self) -> int:
        return len(self.__cache_node_public_keys)

    def __len__(self) -> int:
        return self.get_size()

    def __init_item(self, node_public_key: NodePublicKey, node_address: NodeAddress):
        node_addresses = [node_address]
        self.__filestorage.set(node_public_key=node_public_key, node_addresses=node_addresses)
        self.__cache[node_public_key] = node_addresses
        self.__cache_node_public_keys.append(node_public_key)

    def __update_item(self, node_public_key: NodePublicKey, node_address: NodeAddress):
        node_addresses = self.__cache[node_public_key]

        if node_address > node_addresses[0]:  # Is youngest
            node_addresses.insert(0, node_address)
        else:
            node_addresses.append(node_address)
            node_addresses.sort(reverse=True)

        while len(node_addresses) > NODE_ADDRESSES_QTY:
            node_addresses.pop()  # FIFO

        self.__filestorage.set(node_public_key=node_public_key, node_addresses=node_addresses)

    def add(self, node_public_key: NodePublicKey, node_address: NodeAddress):
        if node_public_key not in self.__cache:
            self.__init_item(node_public_key=node_public_key, node_address=node_address)
        elif node_address not in self.__cache[node_public_key]:
            self.__update_item(node_public_key=node_public_key, node_address=node_address)

    # Without removing just for prototype
    # def remove(self, node_public_key: NodePublicKey):
    #     if node_public_key not in self.__cache:
    #         return
    #     self.__filestorage.remove(node_public_key=node_public_key)
    #     del self.__cache[node_public_key]
    #     self.__cache_node_public_keys.remove(node_public_key)

    def get_first_node_address(self, node_public_key: NodePublicKey) -> NodeAddress:
        return self.__cache[node_public_key][0]

    def iter_node_addresses(self, node_public_key: NodePublicKey) -> Iterator[NodeAddress]:
        for node_address in self.__cache[node_public_key]:
            yield node_address

    def get_random_node_public_key(self) -> NodePublicKey:
        return random.choice(self.__cache_node_public_keys)

    def close(self):
        self.__filestorage.close()

    def __del__(self):
        self.close()
