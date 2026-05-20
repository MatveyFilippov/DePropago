from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import TypeVar
import orjson
from ..node_keys import NodeKeys, NodePublicKey
from ...messages import Message, Payload


def sign_data(author: NodeKeys, data: bytes) -> str:
    signature_bytes = author.node_secret_key.sign(data)
    return urlsafe_b64encode(signature_bytes).decode("ASCII")


def verify_data_sign(author: NodePublicKey, data: bytes, signature: str) -> bool:
    try:
        signature_bytes = urlsafe_b64decode(signature.encode("ASCII"))
        author.key.verify(signature=signature_bytes, data=data)
        return True
    except Exception:  # TODO: Narrow down the exception clause
        return False


P = TypeVar('P', bound=Payload)


class MessageSignatureUtils:
    @staticmethod
    def get_payload_bytes_deterministic(payload: Payload) -> bytes:
        return orjson.dumps(payload.to_dict(), option=orjson.OPT_SORT_KEYS)

    @classmethod
    def get_signed_message(cls, node_keys: NodeKeys, payload: P) -> Message[P]:
        payload_bytes = cls.get_payload_bytes_deterministic(payload=payload)
        signature = sign_data(author=node_keys, data=payload_bytes)
        return Message(
            author=node_keys.node_public_key.str,
            payload=payload,
            signature=signature,
        )

    @classmethod
    def verify_message(cls, signed_message: Message) -> bool:
        payload_bytes = cls.get_payload_bytes_deterministic(payload=signed_message.payload)
        author_node_public_key = NodePublicKey.from_str(signed_message.author)
        return verify_data_sign(
            author=author_node_public_key,
            data=payload_bytes,
            signature=signed_message.signature,
        )
