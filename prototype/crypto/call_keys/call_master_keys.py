from uuid import UUID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF, HKDFExpand
from .ephemeral import CallEphemeralSharedSecret
from ...crypto.node_keys import NodePublicKey


HKDF_HASH = hashes.SHA256()
CALL_MASTER_SEED_HKDF_SALT = "DePropago_VoIP".encode("ASCII")
CALL_MASTER_KEY_BYTES = 16
CALL_MASTER_SALT_BYTES = 14
CALL_AUTH_KEY_BYTES = 20
CALL_MASTER_KEY_INFO_APPENDER = "SRTP_Key"
CALL_MASTER_SALT_INFO_APPENDER = "SRTP_Salt"
CALL_AUTH_KEY_INFO_APPENDER = "SRTP_Auth"


class InfoForCallMasterKeyesDerive:
    CONCATENATOR = ":"

    __slots__ = ("__concatenation_tuple",)

    def __init__(self, *to_concatenation: str):
        self.__concatenation_tuple: tuple[str, ...] = to_concatenation

    def get_bytes_with(self, *to_concatenation: str) -> bytes:
        return self.CONCATENATOR.join(self.__concatenation_tuple + to_concatenation).encode("ASCII")


def hkdf_extract(salt: bytes, key_material: bytes) -> bytes:
    return HKDF.extract(algorithm=HKDF_HASH, salt=salt, key_material=key_material)


def hkdf_expand(length: int, info: bytes, key_material: bytes) -> bytes:
    return HKDFExpand(algorithm=HKDF_HASH, length=length, info=info).derive(key_material=key_material)


class CallMasterKeyes:
    __slots__ = ("__call_master_key", "__call_master_salt", "__call_auth_key")

    def __init__(self, call_ephemeral_shared_secret: CallEphemeralSharedSecret, caller_node_public_key: NodePublicKey, callee_node_public_key: NodePublicKey, call_uuid: UUID):
        call_master_seed = hkdf_extract(
            salt=CALL_MASTER_SEED_HKDF_SALT, key_material=call_ephemeral_shared_secret.raw_bytes,
        )
        info = InfoForCallMasterKeyesDerive(
            caller_node_public_key.str, callee_node_public_key.str, str(call_uuid),
        )

        self.__call_master_key: bytes = hkdf_expand(
            length=CALL_MASTER_KEY_BYTES,
            info=info.get_bytes_with(CALL_MASTER_KEY_INFO_APPENDER),
            key_material=call_master_seed,
        )
        self.__call_master_salt: bytes = hkdf_expand(
            length=CALL_MASTER_SALT_BYTES,
            info=info.get_bytes_with(CALL_MASTER_SALT_INFO_APPENDER),
            key_material=call_master_seed,
        )
        self.__call_auth_key: bytes = hkdf_expand(
            length=CALL_AUTH_KEY_BYTES,
            info=info.get_bytes_with(CALL_AUTH_KEY_INFO_APPENDER),
            key_material=call_master_seed,
        )

    @property
    def call_master_key(self) -> bytes:
        return self.__call_master_key

    @property
    def call_master_salt(self) -> bytes:
        return self.__call_master_salt

    @property
    def call_auth_key(self) -> bytes:
        return self.__call_auth_key
