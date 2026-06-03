from abc import ABC, abstractmethod
import asyncio
from asyncio import Task
from datetime import datetime, timedelta, timezone
import logging
import random
import socket
from typing import TypeVar
from ..crypto.node_keys import NodeKeys, NodePublicKey
from ..crypto.utils import MessageSignatureUtils
from ..messages import Message, Payload
from ..messages.models import UpdatePayload
from ..node_catalogue import NodeAddress, NodesTable


log = logging.getLogger("depropago.network.node")
P = TypeVar('P', bound=Payload)


class Node(ABC):
    @staticmethod
    async def send_message_by_temp_udp_socket(message: Message, address: tuple[str, int]):
        loop = asyncio.get_event_loop()
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        log.debug("setup temp socket")
        data = message.to_json()
        try:
            await loop.sock_sendto(temp_socket, data, address)
            log.debug("send %s to %s:%s by temp socket", data, address[0], address[1])
        finally:
            temp_socket.close()
            log.debug("close temp socket")

    def __init__(self, node_keys: NodeKeys, local_port: int = 0):
        self._node_keys: NodeKeys = node_keys

        self.__main_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__main_socket.setblocking(False)
        self.__main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)  # Raise buffer for voice traffic
        self.__main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)  # Raise buffer for voice traffic
        self.__main_socket.bind(("0.0.0.0", local_port))
        address = self.__main_socket.getsockname()
        log.debug("setup main socket on %s:%s", address[0], address[1])

        self.__received_queue: asyncio.Queue[tuple[bytes, tuple[str, int]]] = asyncio.Queue()

        self.__received_queue_listener_task: Task | None = None
        self.__main_socket_listener_task: Task | None = None

    def __del__(self):
        self.__main_socket.close()
        log.debug("main socket closed")

    @property
    def node_keys(self) -> NodeKeys:
        return self._node_keys

    def create_message(self, payload: P) -> Message[P]:
        return MessageSignatureUtils.get_signed_message(node_keys=self._node_keys, payload=payload)

    async def send_message(self, message: Message, address: tuple[str, int]):
        data = message.to_json()
        loop = asyncio.get_event_loop()
        await loop.sock_sendto(self.__main_socket, data, address)
        log.debug("send %s to %s:%s by main socket", data, address[0], address[1])

    async def create_and_send_message(self, payload: Payload, address: tuple[str, int]):
        message = self.create_message(payload=payload)
        await self.send_message(message=message, address=address)

    async def start(self) -> tuple[str, int]:
        address = self.__main_socket.getsockname()

        self.__received_queue_listener_task = asyncio.create_task(
            self.__received_queue_listener(), name=f"node[{self._node_keys.node_public_key.str}] received queue listener",
        )
        log.debug("setup listener for received queue")

        self.__main_socket_listener_task = asyncio.create_task(
            self.__main_socket_listener(), name=f"node[{self._node_keys.node_public_key.str}] main socket[{address[0]}:{address[1]}] listener",
        )
        log.debug("setup listener for main socket")

        return address

    async def stop(self):
        if self.__main_socket_listener_task:
            log.debug("cancelling listener for main socket")
            self.__main_socket_listener_task.cancel()
            self.__main_socket_listener_task = None
        if self.__received_queue_listener_task:
            log.debug("cancelling listener for received queue")
            self.__received_queue_listener_task.cancel()
            self.__received_queue_listener_task = None

    async def __main_socket_listener(self):
        log.debug("starting main socket listener")
        try:
            loop = asyncio.get_event_loop()
            while True:
                try:
                    log.debug("waiting data from main socket")
                    data, address = await loop.sock_recvfrom(self.__main_socket, 65535)
                    log.debug("receive %s from %s:%s by main socket", data, address[0], address[1])
                    await self.__received_queue.put((data, address))
                    log.debug("put %s & %s:%s to received queue", data, address[0], address[1])
                except Exception as ex:
                    log.error("faced with unexpected exception in main socket listener", exc_info=ex)
                    continue
        except asyncio.CancelledError:
            log.debug("main socket listener canceled")

    async def __received_queue_listener(self):
        log.debug("starting received queue listener")
        try:
            while True:
                try:
                    log.debug("waiting data & address from received queue")
                    data, address = await self.__received_queue.get()
                    log.debug("get %s & %s:%s from received queue", data, address[0], address[1])
                    await self.__handle_received_data_and_address(data=data, address=address)
                except asyncio.TimeoutError:
                    continue
                except Exception as ex:
                    log.error("faced with unexpected exception in received queue listener", exc_info=ex)
                    continue
        except asyncio.CancelledError:
            log.debug("received queue listener canceled")

    async def __handle_received_data_and_address(self, data: bytes, address: tuple[str, int]):
        log.debug("parsing message from %s", data)
        try:
            message = Message.from_json(data)
        except Exception as ex:
            log.error("can't parse message from %s", data, exc_info=ex)
            return

        log.debug("verifying %s", message)
        if not MessageSignatureUtils.verify_message(message):
            log.warning("%s verification failed", message)
            return

        log.debug("start processing %s from %s:%s", message, address[0], address[1])
        await self._process_received(message=message, address=address)
        log.debug("successfully process %s from %s:%s", message, address[0], address[1])

    @abstractmethod
    async def _process_received(self, message: Message, address: tuple[str, int]):
        ...


class NodeSupportedUpdates(Node, ABC):
    RECEIVED_UPDATE_TTL = timedelta(minutes=60)

    def __init__(self, nodes_table: NodesTable, node_keys: NodeKeys, local_port: int = 0):
        super().__init__(node_keys=node_keys, local_port=local_port)

        self._nodes_table = nodes_table

        self.__updates_about_another_node_sender_task: Task | None = None
        self.__updates_about_this_node_sender_task: Task | None = None

    @property
    def nodes_table(self) -> NodesTable:
        return self._nodes_table

    async def add_this_node_address_to_nodes_table(self):  # Call it before share NodeTable
        self._nodes_table.add(
            node_public_key=self._node_keys.node_public_key,
            node_address=NodeAddress.from_message(
                message=self.create_message(
                    payload=(await self._get_update_about_this_node_payload())
                ),
            ),
        )

    async def start(self) -> tuple[str, int]:
        self.__updates_about_another_node_sender_task = asyncio.create_task(
            self.__updates_about_another_node_sender(), name=f"node[{self._node_keys.node_public_key.str}] updates about another node sender",
        )
        log.debug("setup sender for updates about another node")

        self.__updates_about_this_node_sender_task = asyncio.create_task(
            self.__updates_about_this_node_sender(), name=f"node[{self._node_keys.node_public_key.str}] updates about this node sender",
        )
        log.debug("setup sender for updates about this node")

        return await super().start()

    async def stop(self):
        if self.__updates_about_this_node_sender_task:
            log.debug("cancelling sender for updates about this node")
            self.__updates_about_this_node_sender_task.cancel()
            self.__updates_about_this_node_sender_task = None
        if self.__updates_about_another_node_sender_task:
            log.debug("cancelling sender for updates about another node")
            self.__updates_about_another_node_sender_task.cancel()
            self.__updates_about_another_node_sender_task = None

        return await super().stop()

    async def _process_received_update(self, message: Message[UpdatePayload]) -> bool:  # Do not forget to use it in child_class._process_received(...)
        if datetime.now(tz=timezone.utc) - datetime.fromtimestamp(message.payload.timestamp, tz=timezone.utc) > self.RECEIVED_UPDATE_TTL:
            log.info("received 'update' message is out of TTL, skip processing")
            return False
        node_address = NodeAddress.from_message(message=message)
        node_public_key = NodePublicKey.from_str(node_public_key_str=message.author)
        if node_public_key == self._node_keys.node_public_key:
            log.info("received 'update' message is about this node, skip processing")
            return False
        self._nodes_table.add(node_public_key=node_public_key, node_address=node_address)
        log.info("extract node address from 'update' message and add it to nodes table for node with public key '%s'", node_public_key.str)
        return True

    async def __updates_about_another_node_sender(self):
        log.debug("starting updates about another node sender")
        try:
            while True:
                try:
                    target_node_public_key = self._nodes_table.get_random_node_public_key()
                    if target_node_public_key == self._node_keys.node_public_key:
                        continue
                    subject_node_public_key = self._nodes_table.get_random_node_public_key()
                    if subject_node_public_key == target_node_public_key:
                        continue
                    target_node_address = self._nodes_table.get_first_node_address(target_node_public_key)
                    subject_node_address = self._nodes_table.get_first_node_address(subject_node_public_key)

                    log.info("sending 'update' message about node with public key '%s' to node with public key '%s'", subject_node_public_key.str, target_node_public_key.str)
                    await self.send_message(
                        message=subject_node_address.to_message(author=subject_node_public_key),
                        address=target_node_address.address,
                    )

                    await asyncio.sleep(random.randint(30, 120))
                except Exception as ex:
                    log.error("faced with unexpected exception in updates about another node sender", exc_info=ex)
                    continue
        except asyncio.CancelledError:
            log.debug("updates about another node sender canceled")
            return

    async def __updates_about_this_node_sender(self):
        log.debug("starting updates about this node sender")
        try:
            while True:
                try:
                    target_node_public_key = self._nodes_table.get_random_node_public_key()
                    if target_node_public_key == self._node_keys.node_public_key:
                        continue
                    target_node_address = self._nodes_table.get_first_node_address(target_node_public_key)

                    log.info("sending 'update' message about this node to node with public key '%s'", target_node_public_key.str)
                    await self.create_and_send_message(
                        payload=(await self._get_update_about_this_node_payload()),
                        address=target_node_address.address,
                    )

                    await asyncio.sleep(random.randint(300, 540))
                except Exception as ex:
                    log.error("faced with unexpected exception in updates about this node sender", exc_info=ex)
                    continue
        except asyncio.CancelledError:
            log.debug("updates about this node sender canceled")
            return

    @abstractmethod
    async def _get_update_about_this_node_payload(self) -> UpdatePayload:
        ...
