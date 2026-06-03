import asyncio
from datetime import datetime, timezone
import logging
import time
from prototype.crypto.node_keys import NodeKeys, NodeSeedPhrase
from prototype.crypto.utils import MessageSignatureUtils
from prototype.messages.models import UpdatePayload
from prototype.network import ReachableNode
from prototype.node_catalogue import NodeAddress, NodesFileStorageLMDB, NodesTable


IP = "SET.IP.RIGHT.HERE"
PORT = 1212

logging.basicConfig(
    encoding="UTF-8",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(filename="DePropagoFirstNode.log", encoding="UTF-8", mode="a"),
        logging.StreamHandler(),
    ],
)
logging.Formatter.formatTime = (
    lambda self, record, datefmt=None: (
        datetime
        .fromtimestamp(record.created, tz=timezone.utc)
        .isoformat(timespec='milliseconds')
    )
)

NODE_KEYS = NodeKeys.from_node_seed_phrase(
    NodeSeedPhrase(  # Or use NodeSeedPhrase.generate()
        "paste here 24 words (mnemonic phrase)",
    ),
)
NODES_FILESTORAGE = NodesFileStorageLMDB(dir_path="./ncfs")  # Node catalogue NodesFileStorage
NODES_FILESTORAGE.open(readonly=False)
NODES_FILESTORAGE.set(
    node_public_key=NODE_KEYS.node_public_key,
    node_addresses=[
        NodeAddress.from_message(
            message=MessageSignatureUtils.get_signed_message(
                node_keys=NODE_KEYS,
                payload=UpdatePayload(
                    timestamp=int(time.time()),
                    ip=IP,
                    port=PORT,
                ),
            ),
        ),
    ],
)
NODES_FILESTORAGE.close()
NODES_TABLE = NodesTable(based_on=NODES_FILESTORAGE)
if NODES_TABLE.get_size() == 1:  # Add death node, for correct work size must be >= 2
    death_node_keys = NodeKeys.from_node_seed_phrase(NodeSeedPhrase.generate())
    NODES_TABLE.add(
        node_public_key=death_node_keys.node_public_key,
        node_address=NodeAddress.from_message(
            message=MessageSignatureUtils.get_signed_message(
                node_keys=death_node_keys,
                payload=UpdatePayload(
                    timestamp=int(time.time()),
                    ip="8.8.8.8",
                    port=1212,
                ),
            ),
        ),
    )


async def main():
    first_node = ReachableNode(
        node_keys=NODE_KEYS,
        nodes_table=NODES_TABLE,
        public_ip=IP,
        public_port=PORT,
    )

    try:
        await first_node.start()
        while True:
            await asyncio.sleep(1)
    finally:
        await first_node.stop()


if __name__ == "__main__":
    asyncio.run(main())
