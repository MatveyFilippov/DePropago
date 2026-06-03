from dataclasses import dataclass
from .payload import Payload


@dataclass(frozen=True, kw_only=True, slots=True)
class UpdatePayload(Payload):
    _type_name = "Update"

    timestamp: int
    ip: str
    port: int


@dataclass(frozen=True, kw_only=True, slots=True)
class WhoAmIPayload(Payload):
    _type_name = "WhoAmI"


@dataclass(frozen=True, kw_only=True, slots=True)
class WhoAmIResponsePayload(Payload):
    _type_name = "WhoAmI_Response"

    ip: str
    port: int


@dataclass(frozen=True, kw_only=True, slots=True)
class ReachabilityCheckPayload(Payload):
    _type_name = "ReachabilityCheck"


@dataclass(frozen=True, kw_only=True, slots=True)
class KeepAlivePayload(Payload):
    _type_name = "KeepAlive"

    timestamp: int


# TODO: design Payloads
