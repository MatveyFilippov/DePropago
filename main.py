"""DePropago"""
import asyncio
from datetime import datetime, timezone
import logging
import os.path
import shutil
import sys
from prototype.crypto.node_keys import NodeKeys, NodeSeedPhrase
from prototype.network import ReachableNode, UnreachableNode, get_node
from prototype.node_catalogue import NodesFileStorage, NodesFileStorageLMDB, NodesTable


logging.basicConfig(
    encoding="UTF-8",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(filename="DePropago.log", encoding="UTF-8", mode="a"),
        # logging.StreamHandler(),
    ],
)
logging.Formatter.formatTime = (
    lambda self, record, datefmt=None: (
        datetime
        .fromtimestamp(record.created, tz=timezone.utc)
        .isoformat(timespec='milliseconds')
    )
)


class NCFS:  # Node catalogue FileStorage
    NCFS_DIR_PATH = "ncfs"
    NCFS_DATA_FILE_NAME =  "data.mdb"
    NCFS_DATA_PATH = os.path.join(NCFS_DIR_PATH, NCFS_DATA_FILE_NAME)
    NCFS_DATA_EXPORT_FILE_NAME = "data_export.ncfs"

    @classmethod
    def export(cls) -> str:
        export_file_path = shutil.copy(cls.NCFS_DATA_PATH, cls.NCFS_DATA_EXPORT_FILE_NAME)
        print("Successfully export NodesFileStorage!")
        print(f"Now you can share file '{export_file_path}' to invite new Node.")
        return export_file_path

    @classmethod
    async def export_with(cls, node: ReachableNode | UnreachableNode) -> str:
        await node.add_this_node_address_to_nodes_table()
        return cls.export()

    @classmethod
    def __import(cls) -> bool:
        try:
            os.makedirs(cls.NCFS_DIR_PATH, exist_ok=True)
            shutil.copy(cls.NCFS_DATA_EXPORT_FILE_NAME, cls.NCFS_DATA_PATH)
            return True
        except FileNotFoundError:
            return False

    @classmethod
    def get(cls) -> NodesFileStorage:
        if not (os.path.exists(cls.NCFS_DATA_PATH) or cls.__import()):
            print("Can't work without NodesFileStorage!")
            print(f"If you have '{cls.NCFS_DATA_EXPORT_FILE_NAME}' file, it should be located in the same directory as the project's entry point.")
            sys.exit(2)
        return NodesFileStorageLMDB(dir_path=cls.NCFS_DIR_PATH)


def login() -> NodeKeys:
    print("Welcome to DePropago!")
    print(" 1. Sign in (by your NodeSeedPhrase)")
    print(" 2. Sign up (by new account)")
    print(" 3. Exit")
    login_choose = None
    while login_choose is None:
        try:
            login_choose = int(input("Choose [1-3]: "))
            if login_choose not in {1, 2, 3}:
                raise ValueError("Available only [1, 2, 3]")
        except ValueError:
            login_choose = None
            print("Invalid input, try again...")
    if login_choose == 3:
        sys.exit(0)
    if login_choose == 2:
        print("\nATTENTION! Remind your new NodeSeedPhrase, it will be the only way to log in to your account:\n")
        print(NodeSeedPhrase.generate())
        input("\nPress ENTER to continue...")
    print("Input your NodeSeedPhrase.")
    words = input("24 words (sep by space): ")
    while not NodeSeedPhrase.validate(words):
        print("Invalid input, try again...")
        words = input("24 words (sep by space): ")
    return NodeKeys.from_node_seed_phrase(NodeSeedPhrase(words))


async def main():
    nodes_table = NodesTable(based_on=NCFS.get())
    node_keys = login()
    print("Connecting to network...")
    node = await get_node(node_keys=node_keys, nodes_table=nodes_table)  # TODO: monitor network interfaces and redefine the node if change IP
    print(f"Your NodePublicKey is '{node.node_keys.node_public_key}'")

    try:
        await node.start()
        while True:
            await asyncio.sleep(1)
    finally:
        await node.stop()


if __name__ == "__main__":
    asyncio.run(main())
