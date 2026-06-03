from dataclasses import dataclass
from .payload import Payload


@dataclass(frozen=True, kw_only=True, slots=True)
class UpdatePayload(Payload):
    _type_name = "Update"

    timestamp: int
    ip: str
    port: int


# TODO: design Payloads
