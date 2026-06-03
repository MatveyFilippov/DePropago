from abc import ABC
from dataclasses import asdict
from types import MappingProxyType
from typing import Any, ClassVar, Type


_PAYLOAD_REGISTRY: dict[str, Type['Payload']] = {}


# @dataclass(frozen=True, kw_only=True, slots=True)  # Child class must be dataclass
class Payload(ABC):
    __slots__ = ("_dict_cache",)

    _type_name: ClassVar[str]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not (hasattr(cls, "_type_name") and cls._type_name):
            cls._type_name = cls.__name__
        _PAYLOAD_REGISTRY[cls._type_name] = cls

    @classmethod
    def type_name(cls) -> str:
        return cls._type_name

    def to_dict(self) -> dict[str, Any]:
        if not hasattr(self, "_dict_cache"):
            data = asdict(self)
            data["type"] = self._type_name
            object.__setattr__(self, "_dict_cache", data)
        return self._dict_cache.copy()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Payload':
        type_name = data.pop("type")
        payload_cls = _PAYLOAD_REGISTRY[type_name]
        obj = payload_cls(**data)
        data["type"] = type_name
        object.__setattr__(obj, "_dict_cache", MappingProxyType(data.copy()))
        return obj
