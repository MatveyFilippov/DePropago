import asyncio
from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Iterator
from .node import NodeSupportedUpdates
from ..crypto.node_keys import NodeKeys, NodePublicKey
from ..messages import Message
from ..messages.models import (
    KeepAlivePayload, ReachabilityCheckPayload, UpdatePayload, WhoAmIPayload,
    WhoAmIResponsePayload,
)
from ..node_catalogue import NodesTable


log = logging.getLogger("depropago.network.reachablenode")


class EndpointNodes:
    __slots__ = ("__dict",)

    CLEAN_OLD_TTL = timedelta(minutes=60)

    def __init__(self):
        self.__dict: dict[NodePublicKey, tuple[datetime, str, int]] = {}

    def __clean_old(self):
        now = datetime.now(tz=timezone.utc)
        to_clean = []
        for node_public_key, value in self.__dict.items():
            if now - value[0] > self.CLEAN_OLD_TTL:
                to_clean.append(node_public_key)
        for node_public_key in to_clean:
            del self.__dict[node_public_key]

    def set(self, node_public_key: NodePublicKey, received_at: int, address: tuple[str, int]):
        self.__dict[node_public_key] = (
            datetime.fromtimestamp(received_at, tz=timezone.utc),
            address[0],
            address[1],
        )

    def get(self, node_public_key: NodePublicKey) -> tuple[str, int] | None:
        self.__clean_old()
        value = self.__dict.get(node_public_key)
        if value is None:
            return None
        return value[1], value[2]

    def iter(self) -> Iterator[tuple[NodePublicKey, tuple[str, int]]]:
        self.__clean_old()
        for node_public_key, value in self.__dict.items():
            yield node_public_key, (value[1], value[2])


class ReachableNode(NodeSupportedUpdates):
    def __init__(self, nodes_table: NodesTable, node_keys: NodeKeys, public_ip: str, public_port: int):
        super().__init__(nodes_table=nodes_table, node_keys=node_keys, local_port=public_port)

        self._public_ip: str = public_ip
        self._public_port: int = public_port
        self._endpoint_nodes: EndpointNodes = EndpointNodes()

        log.info("init reachable node on %s:%s", public_ip, public_port)

    @property
    def public_ip(self) -> str:
        return self._public_ip

    @property
    def public_port(self) -> int:
        return self._public_port

    async def _process_received(self, message: Message, address: tuple[str, int]):
        message_payload_type = message.payload.type_name()
        if message_payload_type == UpdatePayload.type_name():
            is_ok = await self._process_received_update(message=message)
            if is_ok:
                await self.__duplicate_received_update_to_all_endpoint_nodes(message=message)
        elif message_payload_type == KeepAlivePayload.type_name():
            await self._process_received_keep_alive(message=message, address=address)
        elif message_payload_type == WhoAmIPayload.type_name():
            await self._process_received_who_am_i(message=message, address=address)
        else:
            log.warning("receive message %s with unexpected type from %s:%s, will not process it", message, address[0], address[1])

    async def _process_received_keep_alive(self, message: Message[KeepAlivePayload], address: tuple[str, int]):
        node_public_key = NodePublicKey.from_str(message.author)
        log.info("receive 'keep_alive' request from node with public key '%s'", node_public_key.str)
        self._endpoint_nodes.set(
            node_public_key=node_public_key,
            received_at=message.payload.timestamp,
            address=address,
        )
        log.debug("add endpoint node with public key '%s', sending 'update' message about this node as response", node_public_key.str)
        await self.create_and_send_message(
            payload=(await self._get_update_about_this_node_payload()),
            address=address,
        )

    async def __duplicate_received_update_to_all_endpoint_nodes(self, message: Message[UpdatePayload]):
        for node_public_key, address in self._endpoint_nodes.iter():
            log.info("duplicating received 'update' message to endpoint node with public key '%s'", node_public_key.str)
            await self.send_message(message=message, address=address)

    async def _process_received_who_am_i(self, message: Message[WhoAmIPayload], address: tuple[str, int]):
        node_public_key = NodePublicKey.from_str(message.author)
        log.info("receive 'who_am_i' request from node with public key '%s', sending response", node_public_key.str)
        payload = WhoAmIResponsePayload(ip=address[0], port=address[1])
        await self.create_and_send_message(payload=payload, address=address)
        await asyncio.sleep(0.1)
        log.info("sending 'reachability_check' ping to node with public key '%s' by temp socket", node_public_key.str)
        reachability_check_message = self.create_message(payload=ReachabilityCheckPayload())
        await self.send_message_by_temp_udp_socket(message=reachability_check_message, address=address)

    async def _get_update_about_this_node_payload(self) -> UpdatePayload:
        return UpdatePayload(
            timestamp=int(time.time()),
            ip=self._public_ip,
            port=self._public_port,
        )
