import asyncio
from enum import Enum, auto
import logging
from .node import Node
from .reachable_node import ReachableNode
from .unreachable_node import UnreachableNode
from ..crypto.node_keys import NodeKeys
from ..messages import Message
from ..messages.models import ReachabilityCheckPayload, WhoAmIPayload, WhoAmIResponsePayload
from ..node_catalogue import NodesTable


log = logging.getLogger("depropago.network.discovery")


class NodeType(Enum):
    REACHABLE = auto()
    UNREACHABLE = auto()


class DiscoveryNode(Node):
    WAIT_SECONDS = 5

    def __init__(self, node_keys: NodeKeys):
        super().__init__(node_keys=node_keys)
        self.__requested_address: tuple[str, int] | None = None
        self.__received_address_value: tuple[str, int] | None = None
        self.__is_address_received: asyncio.Event = asyncio.Event()
        self.__is_reachability_check_received: asyncio.Event = asyncio.Event()

    async def _process_received(self, message: Message, address: tuple[str, int]):
        message_payload_type = message.payload.type_name()
        if message_payload_type == WhoAmIResponsePayload.type_name():
            if address != self.__requested_address:
                log.warning(
                    "receive response for 'who_am_i' request from not requested address (wait %s:%s but get %s:%s), will not process it",
                    self.__requested_address[0], self.__requested_address[1], address[0], address[1]
                )
                return
            message: Message[WhoAmIResponsePayload] = message
            self.__received_address_value = (message.payload.ip, message.payload.port)
            self.__is_address_received.set()
            log.debug("receive message response for 'who_am_i' request from %s:%s", address[0], address[1])
        elif message_payload_type == ReachabilityCheckPayload.type_name():
            if address == self.__requested_address:
                log.warning(
                    "receive 'reachability_check' ping from requested address (don't wait %s:%s), will not process it",
                    self.__requested_address[0], self.__requested_address[1],
                )
                return
            self.__is_reachability_check_received.set()
            log.debug("receive 'reachability_check' ping from %s:%s", address[0], address[1])
        else:
            log.warning("receive message %s with unexpected type from %s:%s, will not process it", message, address[0], address[1])

    async def __request_who_am_i(self, address: tuple[str, int]):
        await self.create_and_send_message(payload=WhoAmIPayload(), address=address)

    async def __wait_who_am_i_response(self) -> bool:
        try:
            await asyncio.wait_for(self.__is_address_received.wait(), timeout=self.WAIT_SECONDS)
            return True
        except asyncio.TimeoutError:
            return False

    async def __wait_reachability_check_ping(self) -> bool:
        try:
            await asyncio.wait_for(self.__is_reachability_check_received.wait(), timeout=self.WAIT_SECONDS)
            return True
        except asyncio.TimeoutError:
            return False

    async def __discovery(self, address: tuple[str, int]) -> tuple[str, int, NodeType] | None:
        if self.__requested_address is not None:
            raise ValueError("Discovery already running")
        log.debug("running discovery to %s:%s", address[0], address[1])

        self.__requested_address = address
        self.__received_address_value = None
        self.__is_address_received.clear()
        self.__is_reachability_check_received.clear()

        try:
            await self.__request_who_am_i(address)
            log.info("request 'who_am_i', waiting response")
            if not await self.__wait_who_am_i_response():
                log.info("don't receive response for 'who_am_i' request")
                return None
            log.info("receive response for 'who_am_i' request, waiting 'reachability_check' ping")
            if not await self.__wait_reachability_check_ping():
                log.info("don't receive 'reachability_check' ping")
                return *self.__received_address_value, NodeType.UNREACHABLE
            log.info("receive 'reachability_check' ping")
            return *self.__received_address_value, NodeType.REACHABLE
        finally:
            self.__requested_address = None

    async def run_discovery(self, nodes_table: NodesTable) -> tuple[str, int, NodeType]:
        while True:
            helper_node_public_key = nodes_table.get_random_node_public_key()
            log.info("choose node with public key '%s' as helper", helper_node_public_key)
            for helper_node_address in nodes_table.iter_node_addresses(node_public_key=helper_node_public_key):
                result = await self.__discovery(address=helper_node_address.address)
                if result is not None:
                    log.debug("current public address is %s:%s", result[0], result[1])
                    return result


async def get_node(node_keys: NodeKeys, nodes_table: NodesTable) -> ReachableNode | UnreachableNode:
    log.info("start discovery")

    discovery_node = DiscoveryNode(node_keys=node_keys)
    await discovery_node.start()
    await asyncio.sleep(0.05)
    discovery_result = await discovery_node.run_discovery(nodes_table=nodes_table)
    await discovery_node.stop()

    log.info("end discovery, type is '%s'", discovery_result[2].name.lower())

    if discovery_result[2] == NodeType.REACHABLE:
        return ReachableNode(
            nodes_table=nodes_table,
            node_keys=node_keys,
            public_ip=discovery_result[0],
            public_port=discovery_result[1],
        )
    else:
        return UnreachableNode(
            nodes_table=nodes_table,
            node_keys=node_keys,
        )
