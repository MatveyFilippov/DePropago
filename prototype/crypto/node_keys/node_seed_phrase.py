import hashlib
from mnemonic import Mnemonic


LANGUAGE = "english"
WORDS_QTY = 24
ENTROPY_BYTES = 256
SEED_BYTES = 64
PBKDF2_HASH = "sha512"
PBKDF2_ROUNDS = 2048
PBKDF2_SALT = "DePropago"
PBKDF2_SALT_BYTES = Mnemonic.normalize_string(PBKDF2_SALT).encode("UTF-8")


class NodeSeedPhrase:
    __MNEMONIC = Mnemonic(LANGUAGE)

    @classmethod
    def validate(cls, phrase: str) -> bool:
        return cls.__MNEMONIC.check(phrase)

    def __init__(self, phrase: str):
        if not self.validate(phrase):
            raise ValueError("Invalid NodeSeedPhrase")
        self.__phrase = phrase

    @property
    def node_seed_phrase(self) -> str:
        return self.__phrase

    def __str__(self):
        return self.__phrase

    def get_separate_node_seed_words(self) -> list[str]:
        return self.__phrase.split(sep=self.__MNEMONIC.delimiter, maxsplit=WORDS_QTY)

    def to_node_master_seed(self) -> bytes:
        # return self.__MNEMONIC.to_seed(mnemonic=self.__phrase)  # Cannot be used due to constant salt

        normalized_phrase = Mnemonic.normalize_string(self.__phrase)
        normalized_phrase_bytes = normalized_phrase.encode("UTF-8")

        stretched = hashlib.pbkdf2_hmac(
            hash_name=PBKDF2_HASH,
            password=normalized_phrase_bytes,
            salt=PBKDF2_SALT_BYTES,
            iterations=PBKDF2_ROUNDS,
        )

        return stretched[:SEED_BYTES]

    @classmethod
    def generate(cls) -> 'NodeSeedPhrase':
        node_seed_phrase = cls.__MNEMONIC.generate(strength=ENTROPY_BYTES)
        return cls(phrase=node_seed_phrase)
