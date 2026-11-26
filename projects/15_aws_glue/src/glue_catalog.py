import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional

logger = logging.getLogger("glue_catalog")

class GlueCatalogManager:
    """
    Manages AWS Glue Data Catalog databases and tables using boto3.
    """
    def __init__(self, region_name: str = "us-east-1", aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None):
        try:
            if aws_access_key_id and aws_secret_access_key:
                self.client = boto3.client(
                    "glue",
                    region_name=region_name,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key
                )
            else:
                self.client = boto3.client("glue", region_name=region_name)
            self.is_mock = False
        except Exception as e:
            logger.warning(f"Boto3 client initialization failed ({e}). Using mock client for local execution.")
            self.client = MockGlueBotoClient()
            self.is_mock = True

    def create_database(self, database_name: str, description: str = "") -> bool:
        """Creates a Glue database if it doesn't already exist."""
        try:
            self.client.create_database(
                DatabaseInput={
                    "Name": database_name,
                    "Description": description
                }
            )
            logger.info(f"Glue Database '{database_name}' created successfully.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                logger.info(f"Glue Database '{database_name}' already exists.")
                return True
            else:
                logger.error(f"Error creating Glue Database '{database_name}': {e}")
                raise e

    def get_database(self, database_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a Glue database."""
        try:
            response = self.client.get_database(Name=database_name)
            return response.get("Database")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Glue Database '{database_name}' not found.")
                return None
            else:
                logger.error(f"Error getting Glue Database '{database_name}': {e}")
                raise e

    def delete_database(self, database_name: str) -> bool:
        """Deletes a Glue database and all tables within it."""
        try:
            self.client.delete_database(Name=database_name)
            logger.info(f"Glue Database '{database_name}' deleted successfully.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Glue Database '{database_name}' already deleted or does not exist.")
                return True
            else:
                logger.error(f"Error deleting Glue Database '{database_name}': {e}")
                raise e

    def create_table(
        self,
        database_name: str,
        table_name: str,
        s3_location: str,
        columns: List[Dict[str, str]],
        partition_keys: Optional[List[Dict[str, str]]] = None,
        file_format: str = "parquet",
        classification: str = "parquet"
    ) -> bool:
        """
        Creates a table in the Glue Data Catalog with defined columns, S3 storage descriptor,
        and partitioning scheme.
        """
        serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
        input_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
        output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

        if file_format.lower() == "csv":
            serialization_library = "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
            input_format = "org.apache.hadoop.mapred.TextInputFormat"
            output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"
        elif file_format.lower() == "json":
            serialization_library = "org.openx.data.jsonserde.JsonSerDe"
            input_format = "org.apache.hadoop.mapred.TextInputFormat"
            output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

        table_input = {
            "Name": table_name,
            "Description": f"ETL Metadata table for {table_name}",
            "StorageDescriptor": {
                "Columns": [{"Name": col["name"], "Type": col["type"]} for col in columns],
                "Location": s3_location,
                "InputFormat": input_format,
                "OutputFormat": output_format,
                "Compressed": False,
                "NumberOfBuckets": -1,
                "SerdeInfo": {
                    "SerializationLibrary": serialization_library,
                    "Parameters": {"serialization.format": "1"} if file_format.lower() == "csv" else {}
                }
            },
            "PartitionKeys": [{"Name": pk["name"], "Type": pk["type"]} for pk in partition_keys] if partition_keys else [],
            "TableType": "EXTERNAL_TABLE",
            "Parameters": {
                "classification": classification,
                "typeOfData": "file"
            }
        }

        try:
            self.client.create_table(DatabaseName=database_name, TableInput=table_input)
            logger.info(f"Glue Table '{table_name}' created under database '{database_name}' at location '{s3_location}'.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                logger.info(f"Glue Table '{table_name}' already exists in database '{database_name}'.")
                return True
            else:
                logger.error(f"Error creating Glue Table '{table_name}': {e}")
                raise e

    def get_table(self, database_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a Glue table."""
        try:
            response = self.client.get_table(DatabaseName=database_name, Name=table_name)
            return response.get("Table")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Glue Table '{table_name}' not found in database '{database_name}'.")
                return None
            else:
                logger.error(f"Error getting Glue Table '{table_name}': {e}")
                raise e

    def update_table_schema(self, database_name: str, table_name: str, new_columns: List[Dict[str, str]]) -> bool:
        """Updates the schema of an existing Glue table (adds new columns or updates types)."""
        table_desc = self.get_table(database_name, table_name)
        if not table_desc:
            raise ValueError(f"Table '{table_name}' does not exist in database '{database_name}'. Cannot update schema.")

        # Prepare updated table input payload from existing parameters
        table_input = {
            "Name": table_desc["Name"],
            "StorageDescriptor": table_desc["StorageDescriptor"],
            "PartitionKeys": table_desc.get("PartitionKeys", []),
            "TableType": table_desc.get("TableType", "EXTERNAL_TABLE"),
            "Parameters": table_desc.get("Parameters", {})
        }

        # Apply new column definitions to storage descriptor
        table_input["StorageDescriptor"]["Columns"] = [{"Name": col["name"], "Type": col["type"]} for col in new_columns]

        # Clean parameters that shouldn't be sent back in the update
        keys_to_remove = ["DatabaseName", "CreateTime", "UpdateTime", "CreatedBy", "IsRegisteredWithLakeFormation", "CatalogId", "VersionId", "Owner", "FederatedTable"]
        for key in keys_to_remove:
            table_input.pop(key, None)

        try:
            self.client.update_table(DatabaseName=database_name, TableInput=table_input)
            logger.info(f"Glue Table '{table_name}' schema updated successfully.")
            return True
        except ClientError as e:
            logger.error(f"Error updating Glue Table '{table_name}' schema: {e}")
            raise e

    def delete_table(self, database_name: str, table_name: str) -> bool:
        """Deletes a table from the Glue Data Catalog."""
        try:
            self.client.delete_table(DatabaseName=database_name, Name=table_name)
            logger.info(f"Glue Table '{table_name}' deleted successfully from database '{database_name}'.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.warning(f"Glue Table '{table_name}' not found in database '{database_name}' or already deleted.")
                return True
            else:
                logger.error(f"Error deleting Glue Table '{table_name}': {e}")
                raise e


class MockGlueBotoClient:
    """Mock implementation of the boto3 glue client for local runs and offline unit tests."""
    def __init__(self):
        self.databases = {}
        self.tables = {}

    def create_database(self, DatabaseInput: Dict[str, Any]):
        name = DatabaseInput["Name"]
        if name in self.databases:
            raise ClientError({"Error": {"Code": "AlreadyExistsException", "Message": "Database already exists"}}, "create_database")
        self.databases[name] = DatabaseInput
        return {}

    def get_database(self, Name: str) -> Dict[str, Any]:
        if Name not in self.databases:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Database not found"}}, "get_database")
        return {"Database": self.databases[Name]}

    def delete_database(self, Name: str):
        if Name not in self.databases:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Database not found"}}, "delete_database")
        del self.databases[Name]
        # Cascade table deletion
        tables_to_delete = [t for t in self.tables if t.startswith(f"{Name}.")]
        for t in tables_to_delete:
            del self.tables[t]
        return {}

    def create_table(self, DatabaseName: str, TableInput: Dict[str, Any]):
        if DatabaseName not in self.databases:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Database not found"}}, "create_table")
        tbl_name = TableInput["Name"]
        key = f"{DatabaseName}.{tbl_name}"
        if key in self.tables:
            raise ClientError({"Error": {"Code": "AlreadyExistsException", "Message": "Table already exists"}}, "create_table")
        self.tables[key] = TableInput
        return {}

    def get_table(self, DatabaseName: str, Name: str) -> Dict[str, Any]:
        key = f"{DatabaseName}.{Name}"
        if key not in self.tables:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Table not found"}}, "get_table")
        return {"Table": self.tables[key]}

    def update_table(self, DatabaseName: str, TableInput: Dict[str, Any]):
        tbl_name = TableInput["Name"]
        key = f"{DatabaseName}.{tbl_name}"
        if key not in self.tables:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Table not found"}}, "update_table")
        self.tables[key] = TableInput
        return {}

    def delete_table(self, DatabaseName: str, Name: str):
        key = f"{DatabaseName}.{Name}"
        if key not in self.tables:
            raise ClientError({"Error": {"Code": "EntityNotFoundException", "Message": "Table not found"}}, "delete_table")
        del self.tables[key]
        return {}
