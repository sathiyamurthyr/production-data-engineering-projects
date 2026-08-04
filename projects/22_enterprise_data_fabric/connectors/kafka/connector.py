"""Kafka Connector - Apache Kafka metadata harvesting."""

from typing import Any

from ...platform.connectors.base import BaseConnector
from ...platform.metadata.models import Asset, AssetType, Column, SensitivityLevel


class KafkaConnector(BaseConnector):
    """Harvest metadata from Apache Kafka."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Kafka connector."""
        super().__init__(config)
        self.platform_name = "kafka"
        self.bootstrap_servers = config.get("bootstrap_servers", "localhost:9092")
        self.security_protocol = config.get("security_protocol", "PLAINTEXT")
        self.sasl_mechanism = config.get("sasl_mechanism", "PLAIN")
        self.sasl_username = config.get("sasl_username", "")
        self.sasl_password = config.get("sasl_password", "")

    def test_connection(self) -> bool:
        """Test connection to Kafka."""
        try:
            from confluent_kafka import Consumer, KafkaException
            conf = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': 'data-fabric-test',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
            }
            if self.security_protocol != "PLAINTEXT":
                conf.update({
                    'security.protocol': self.security_protocol,
                    'sasl.mechanism': self.sasl_mechanism,
                    'sasl.username': self.sasl_username,
                    'sasl.password': self.sasl_password,
                })
            consumer = Consumer(conf)
            cluster_metadata = consumer.list_topics(timeout=5)
            consumer.close()
            return True
        except Exception:
            return False

    def get_assets(self) -> list[Asset]:
        """Retrieve all topics from Kafka."""
        assets = []
        try:
            from confluent_kafka import Consumer
            conf = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': 'data-fabric-metadata',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
            }
            if self.security_protocol != "PLAINTEXT":
                conf.update({
                    'security.protocol': self.security_protocol,
                    'sasl.mechanism': self.sasl_mechanism,
                    'sasl.username': self.sasl_username,
                    'sasl.password': self.sasl_password,
                })
            consumer = Consumer(conf)
            cluster_metadata = consumer.list_topics(timeout=10)
            for topic_name, topic_metadata in cluster_metadata.topics.items():
                if topic_name.startswith('__'):
                    continue
                asset = self._topic_to_asset(topic_name, topic_metadata)
                assets.append(asset)
            consumer.close()
        except Exception as e:
            print(f"Error fetching Kafka assets: {e}")
        return assets

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get specific topic by name."""
        try:
            from confluent_kafka import Consumer
            conf = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': 'data-fabric-metadata',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
            }
            if self.security_protocol != "PLAINTEXT":
                conf.update({
                    'security.protocol': self.security_protocol,
                    'sasl.mechanism': self.sasl_mechanism,
                    'sasl.username': self.sasl_username,
                    'sasl.password': self.sasl_password,
                })
            consumer = Consumer(conf)
            cluster_metadata = consumer.list_topics(timeout=10)
            if asset_id in cluster_metadata.topics:
                topic_metadata = cluster_metadata.topics[asset_id]
                asset = self._topic_to_asset(asset_id, topic_metadata)
                consumer.close()
                return asset
            consumer.close()
        except Exception as e:
            print(f"Error fetching topic {asset_id}: {e}")
        return None

    def get_lineage(self, asset_id: str) -> dict[str, Any]:
        """Get lineage from Kafka topic producers and consumers."""
        # In production, integrate with Kafka Connect and Streams metadata
        return {"nodes": [], "edges": []}

    def get_schema(self, asset_id: str) -> dict[str, Any]:
        """Get schema from Schema Registry."""
        schema_registry_url = self.config.get("schema_registry_url", "")
        if not schema_registry_url:
            return {"schema": None, "version": None}
        try:
            from confluent_kafka.schema_registry import SchemaRegistryClient
            client = SchemaRegistryClient({'url': schema_registry_url})
            # Get latest schema version for topic
            # This would require mapping topic to subject
            return {"schema": None, "version": None}
        except Exception as e:
            print(f"Error fetching schema: {e}")
            return {"schema": None, "version": None}

    def _topic_to_asset(self, topic_name: str, topic_metadata: Any) -> Asset:
        """Convert Kafka topic to Asset."""
        partitions = len(topic_metadata.partitions) if topic_metadata.partitions else 0
        replication_factor = len(topic_metadata.partitions[0].replicas) if topic_metadata.partitions and topic_metadata.partitions[0].replicas else 0
        
        return Asset(
            name=topic_name,
            description=f"Kafka topic with {partitions} partitions, replication factor {replication_factor}",
            asset_type=AssetType.STREAM,
            platform="kafka",
            platform_id=topic_name,
            domain=self.config.get("domain", "default"),
            tags=["kafka", "streaming"],
            sensitivity=SensitivityLevel.INTERNAL,
            metadata={
                "partitions": partitions,
                "replication_factor": replication_factor,
                "bootstrap_servers": self.bootstrap_servers,
            },
        )

    def get_consumer_groups(self) -> list[dict[str, Any]]:
        """Get all consumer groups."""
        consumer_groups = []
        try:
            from confluent_kafka import Consumer, KafkaException
            conf = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': 'data-fabric-metadata',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
            }
            if self.security_protocol != "PLAINTEXT":
                conf.update({
                    'security.protocol': self.security_protocol,
                    'sasl.mechanism': self.sasl_mechanism,
                    'sasl.username': self.sasl_username,
                    'sasl.password': self.sasl_password,
                })
            consumer = Consumer(conf)
            cluster_metadata = consumer.list_topics(timeout=10)
            # In production, use AdminClient to list consumer groups
            consumer.close()
        except Exception as e:
            print(f"Error fetching consumer groups: {e}")
        return consumer_groups

    def get_topic_config(self, topic_name: str) -> dict[str, Any]:
        """Get topic configuration."""
        try:
            from confluent_kafka import Consumer
            conf = {
                'bootstrap.servers': self.bootstrap_servers,
                'group.id': 'data-fabric-metadata',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
            }
            if self.security_protocol != "PLAINTEXT":
                conf.update({
                    'security.protocol': self.security_protocol,
                    'sasl.mechanism': self.sasl_mechanism,
                    'sasl.username': self.sasl_username,
                    'sasl.password': self.sasl_password,
                })
            consumer = Consumer(conf)
            # In production, use AdminClient to describe configs
            consumer.close()
            return {}
        except Exception as e:
            print(f"Error fetching topic config: {e}")
            return {}

    def get_acl(self, topic_name: str) -> list[dict[str, Any]]:
        """Get ACLs for a topic."""
        # In production, use AdminClient to describe ACLs
        return []