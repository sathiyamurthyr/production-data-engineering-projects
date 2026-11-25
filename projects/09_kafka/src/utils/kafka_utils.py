"""
Project 09: Apache Kafka for Real-Time Data Engineering
src/utils/kafka_utils.py

Kafka System Utilities & Health Checks.

Provides operational helpers:
- Broker socket connectivity validation with timeouts
- Wait-for-topic readiness polling for integration testing
- Bootstrap servers address parser and validator
"""

import logging
import socket
import time
from typing import List, Tuple

logger = logging.getLogger(__name__)


def parse_bootstrap_servers(bootstrap_servers: str) -> List[Tuple[str, int]]:
    """
    Parse comma-separated bootstrap servers string into (host, port) tuples.
    Example: "kafka1:9092,kafka2:9092" -> [("kafka1", 9092), ("kafka2", 9092)]
    """
    servers = []
    for server in bootstrap_servers.split(","):
        server = server.strip()
        if not server:
            continue
        if ":" in server:
            host, port_str = server.split(":", 1)
            servers.append((host, int(port_str)))
        else:
            servers.append((server, 9092))
    return servers


def check_kafka_connectivity(bootstrap_servers: str, timeout_sec: float = 3.0) -> bool:
    """
    Test TCP socket connection to Kafka bootstrap brokers.
    Returns True if at least one broker responds within timeout.
    """
    server_tuples = parse_bootstrap_servers(bootstrap_servers)

    for host, port in server_tuples:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_sec)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                logger.info("[check_kafka_connectivity] Connected to %s:%d", host, port)
                return True
        except Exception as exc:
            logger.debug("[check_kafka_connectivity] Failed to connect to %s:%d -> %s", host, port, exc)

    logger.warning("[check_kafka_connectivity] Unable to connect to brokers: %s", bootstrap_servers)
    return False


def wait_for_kafka_ready(bootstrap_servers: str, timeout_sec: float = 30.0, retry_interval: float = 2.0) -> bool:
    """
    Poll Kafka connectivity until ready or timeout reached.
    """
    start_time = time.monotonic()
    logger.info("Waiting for Kafka cluster at %s to be ready...", bootstrap_servers)

    while (time.monotonic() - start_time) < timeout_sec:
        if check_kafka_connectivity(bootstrap_servers, timeout_sec=2.0):
            logger.info("Kafka cluster at %s is READY!", bootstrap_servers)
            return True
        time.sleep(retry_interval)

    logger.error("Timed out waiting for Kafka cluster at %s after %.1fs", bootstrap_servers, timeout_sec)
    return False
