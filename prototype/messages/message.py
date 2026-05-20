from typing import Generic, TypeVar
import orjson
from .payload import Payload


class MessageKeys:
    AUTHOR = "author"
    PAYLOAD = "payload"
    SIGNATURE = "signature"


P = TypeVar('P', bound=Payload)


class Message(Generic[P]):
    __slots__ = ("__author", "__payload", "__signature", "__json_cache")

    def __init__(self, author: str, payload: P, signature: str):
        self.__author: str = author
        self.__payload: P = payload
        self.__signature: str = signature
        self.__json_cache: bytes | None = None

    @property
    def author(self) -> str:
        return self.__author

    @property
    def payload(self) -> P:
        return self.__payload

    @property
    def signature(self) -> str:
        return self.__signature

    def to_json(self) -> bytes:
        if self.__json_cache is None:
            self.__json_cache = orjson.dumps(
                {
                    MessageKeys.AUTHOR: self.__author,
                    MessageKeys.PAYLOAD: self.__payload.to_dict(),
                    MessageKeys.SIGNATURE: self.__signature,
                },
            )
        return self.__json_cache

    @classmethod
    def from_json(cls, data: bytes) -> 'Message':
        json_dict = orjson.loads(data)
        obj = cls(
            author=json_dict[MessageKeys.AUTHOR],
            payload=Payload.from_dict(json_dict[MessageKeys.PAYLOAD]),
            signature=json_dict[MessageKeys.SIGNATURE],
        )
        obj.__json_cache = data
        return obj
