from typing import Any, Generic, TypeVar
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

    def __repr__(self) -> str:
        return f"Message(author={self.__author!r}, payload={self.__payload!r}, signature={self.__signature!r})"

    def to_dict(self) -> dict[str, Any]:
        return {
            MessageKeys.AUTHOR: self.__author,
            MessageKeys.PAYLOAD: self.__payload.to_dict(),
            MessageKeys.SIGNATURE: self.__signature,
        }

    def to_json(self) -> bytes:
        if self.__json_cache is None:
            _dict = self.to_dict()
            self.__json_cache = orjson.dumps(_dict)
        return self.__json_cache

    @classmethod
    def from_dict(cls, _dict: dict[str, Any]):
        return cls(
            author=_dict[MessageKeys.AUTHOR],
            payload=Payload.from_dict(_dict[MessageKeys.PAYLOAD]),
            signature=_dict[MessageKeys.SIGNATURE],
        )

    @classmethod
    def from_json(cls, _json: bytes) -> 'Message':
        _dict = orjson.loads(_json)
        obj = cls.from_dict(_dict)
        obj.__json_cache = _json
        return obj
