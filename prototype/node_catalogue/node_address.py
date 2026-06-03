from ..crypto.node_keys import NodePublicKey
from ..messages import Message
from ..messages.models import UpdatePayload


class NodeAddress:
    __slots__ = ("__ip", "__port", "__timestamp", "__signature")

    def __init__(self, ip: str, port: int, timestamp: int, origin_message_signature: str):
        self.__ip: str = ip
        self.__port: int = port
        self.__timestamp: int = timestamp
        self.__signature: str = origin_message_signature

    @property
    def address(self) -> tuple[str, int]:
        return self.__ip, self.__port

    @property
    def ip(self) -> str:
        return self.__ip

    @property
    def port(self) -> int:
        return self.__port

    @property
    def creation_timestamp(self) -> int:
        return self.__timestamp

    @property
    def origin_message_signature(self) -> str:
        return self.__signature

    def __repr__(self) -> str:
        return f"NodeAddress(ip={self.__ip!r}, port={self.__port!r}, timestamp={self.__timestamp!r}, signature={self.__signature!r})"

    def __hash__(self):
        return hash((self.__signature, self.__timestamp))

    def __eq__(self, other):
        if isinstance(other, NodeAddress):
            return self.__signature == other.__signature and self.__timestamp == other.__timestamp
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, NodeAddress):
            return self.__timestamp <= other.__timestamp
        return NotImplemented

    def __lt__(self, other) -> bool:
        if isinstance(other, NodeAddress):
            return self.__timestamp < other.__timestamp
        return NotImplemented

    def __ge__(self, other) -> bool:
        if isinstance(other, NodeAddress):
            return self.__timestamp >= other.__timestamp
        return NotImplemented

    def __gt__(self, other) -> bool:
        if isinstance(other, NodeAddress):
            return self.__timestamp > other.__timestamp
        return NotImplemented

    def to_message(self, author: NodePublicKey) -> Message[UpdatePayload]:
        return Message(
            author=author.str,
            payload=UpdatePayload(
                timestamp=self.__timestamp,
                ip=self.__ip,
                port=self.__port,
            ),
            signature=self.__signature,
        )

    @classmethod
    def from_message(cls, message: Message[UpdatePayload]) -> 'NodeAddress':
        return cls(
            ip=message.payload.ip,
            port=message.payload.port,
            timestamp=message.payload.timestamp,
            origin_message_signature=message.signature,
        )
