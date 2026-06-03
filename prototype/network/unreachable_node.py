import asyncio
from asyncio import Task
from datetime import datetime, timedelta, timezone
import logging
import random
import time
from .node import NodeSupportedUpdates
from ..crypto.node_keys import NodeKeys, NodePublicKey
from ..messages import Message
from ..messages.models import KeepAlivePayload, UpdatePayload
from ..node_catalogue import NodesTable


log = logging.getLogger("depropago.network.unreachablenode")


class ReleyNodesPublicKeys:
    __slots__ = ("__challengers", "__approved")

    RELEY_QTY = 4  # TODO: provide 4-16, depends on the device resources
    FROZEN_TTL = timedelta(seconds=5)

    def __init__(self):
        self.__challengers: dict[NodePublicKey, datetime] = {}
        self.__approved: list[NodePublicKey] = []

    def __clean_dead_challengers(self):
        now = datetime.now(tz=timezone.utc)
        for node_public_key, born_at in self.__challengers.copy().items():
            if now - born_at > self.FROZEN_TTL:
                del self.__challengers[node_public_key]

    def __add_youngest_approved(self, node_public_key: NodePublicKey):
        while node_public_key in self.__approved:
            self.__approved.remove(node_public_key)
        self.__approved.append(node_public_key)

    def __pop_oldest_approved(self) -> NodePublicKey:
        return self.__approved.pop(0)

    def approve(self, node_public_key: NodePublicKey) -> bool:
        self.__clean_dead_challengers()
        if node_public_key not in self.__challengers:
            return False
        del self.__challengers[node_public_key]
        while len(self.__approved) >= self.RELEY_QTY:
            self.__pop_oldest_approved()
        self.__add_youngest_approved(node_public_key)
        return True

    def get_next_challenger(self, nodes_table: NodesTable) -> NodePublicKey:
        self.__clean_dead_challengers()
        approved_qty = len(self.__approved)
        if (approved_qty > 0) and (approved_qty + len(self.__challengers) >= self.RELEY_QTY):
            node_public_key = self.__pop_oldest_approved()
        else:
            node_public_key = nodes_table.get_random_node_public_key()
        self.__challengers[node_public_key] = datetime.now(tz=timezone.utc)
        return node_public_key

    async def get_random_approved(self) -> NodePublicKey:
        while True:
            if len(self.__approved) > 0:
                return random.choice(self.__approved)
            await asyncio.sleep(0.1)


class UnreachableNode(NodeSupportedUpdates):
    def __init__(self, nodes_table: NodesTable, node_keys: NodeKeys):
        super().__init__(nodes_table=nodes_table, node_keys=node_keys)

        self._reley_nodes_public_keys: ReleyNodesPublicKeys = ReleyNodesPublicKeys()
        self.__reley_connections_alive_keeper_task: Task | None = None

        log.info("init unreachable node")

    async def start(self) -> tuple[str, int]:
        self.__reley_connections_alive_keeper_task = asyncio.create_task(
            self.__reley_connections_alive_keeper(), name=f"node[{self._node_keys.node_public_key.str}] reley connections alive keeper",
        )
        log.debug("setup alive keeper for reley connections")

        return await super().start()

    async def stop(self):
        if self.__reley_connections_alive_keeper_task:
            log.debug("cancelling alive keeper for reley connections")
            self.__reley_connections_alive_keeper_task.cancel()
            self.__reley_connections_alive_keeper_task = None

        return await super().stop()

    async def __reley_connections_alive_keeper(self):
        log.debug("starting reley connections alive keeper")
        sleep_sec = 20 / ReleyNodesPublicKeys.RELEY_QTY
        try:
            while True:
                try:
                    challenger_node_public_key = self._reley_nodes_public_keys.get_next_challenger(nodes_table=self._nodes_table)
                    log.info("challenge node with public key '%s' as reley by sending 'keep_alive' request", challenger_node_public_key.str)

                    challenger_node_address = self._nodes_table.get_first_node_address(challenger_node_public_key)
                    payload = KeepAlivePayload(timestamp=int(time.time()))
                    await self.create_and_send_message(payload=payload, address=challenger_node_address.address)

                    await asyncio.sleep(sleep_sec)
                except Exception as ex:
                    log.error("faced with unexpected exception in reley connections alive keeper", exc_info=ex)
                    continue
        except asyncio.CancelledError:
            log.debug("reley connections alive keeper canceled")
            return

    async def __process_received_update_as_approving_reley(self, message: Message[UpdatePayload]):
        node_public_key = NodePublicKey.from_str(message.author)
        is_approved = self._reley_nodes_public_keys.approve(node_public_key)
        if is_approved:
            log.info("approve node with public key '%s' as reley by received 'update' message", node_public_key.str)
        else:
            log.debug("don't approve node with public key '%s' as reley by received 'update' message", node_public_key.str)

    async def _process_received(self, message: Message, address: tuple[str, int]):
        message_payload_type = message.payload.type_name()
        if message_payload_type == UpdatePayload.type_name():
            is_ok = await self._process_received_update(message=message)
            if is_ok:
                await self.__process_received_update_as_approving_reley(message=message)
        else:
            log.warning("receive message %s with unexpected type from %s:%s, will not process it", message, address[0], address[1])

    async def _get_update_about_this_node_payload(self) -> UpdatePayload:
        reley_node_public_key = await self._reley_nodes_public_keys.get_random_approved()
        log.info("choose reley node with public key '%s' address for creating update payload about this node", reley_node_public_key.str)
        reley_node_address = self._nodes_table.get_first_node_address(reley_node_public_key)
        return UpdatePayload(
            timestamp=int(time.time()),
            ip=reley_node_address.ip,
            port=reley_node_address.port,
        )
