import os
import sys
import pytest

# Set project paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.glue_catalog import GlueCatalogManager

@pytest.fixture
def catalog_manager():
    """Initializes GlueCatalogManager. Automatically falls back to mock boto client locally."""
    return GlueCatalogManager(region_name="us-east-1")

def test_database_lifecycle(catalog_manager):
    """Tests database creation, retrieval, and deletion."""
    db_name = "test_sales_db"
    
    # 1. Create database
    created = catalog_manager.create_database(db_name, "Temporary database for unit testing")
    assert created is True
    
    # 2. Get database details
    db_details = catalog_manager.get_database(db_name)
    assert db_details is not None
    assert db_details["Name"] == db_name
    assert db_details["Description"] == "Temporary database for unit testing"
    
    # 3. Delete database
    deleted = catalog_manager.delete_database(db_name)
    assert deleted is True
    
    # Verify database is deleted
    assert catalog_manager.get_database(db_name) is None

def test_table_lifecycle(catalog_manager):
    """Tests creating, fetching, updating schemas, and deleting catalog tables."""
    db_name = "ecommerce_test_db"
    tbl_name = "sales_test_tbl"
    s3_path = "s3://test-bucket/raw/sales/"
    
    catalog_manager.create_database(db_name, "Mock DB for table tests")
    
    columns = [
        {"name": "order_id", "type": "string"},
        {"name": "revenue", "type": "double"},
        {"name": "order_date", "type": "string"}
    ]
    
    partition_keys = [
        {"name": "region", "type": "string"}
    ]
    
    # 1. Create table
    created = catalog_manager.create_table(
        database_name=db_name,
        table_name=tbl_name,
        s3_location=s3_path,
        columns=columns,
        partition_keys=partition_keys,
        file_format="parquet",
        classification="parquet"
    )
    assert created is True
    
    # 2. Get table and verify structure
    table = catalog_manager.get_table(db_name, tbl_name)
    assert table is not None
    assert table["Name"] == tbl_name
    assert table["TableType"] == "EXTERNAL_TABLE"
    assert table["StorageDescriptor"]["Location"] == s3_path
    
    cols = table["StorageDescriptor"]["Columns"]
    assert len(cols) == 3
    assert cols[0]["Name"] == "order_id"
    assert cols[0]["Type"] == "string"
    
    # 3. Update table schema (add dynamic fields / schema evolution)
    updated_cols = columns + [{"name": "discount", "type": "double"}]
    updated = catalog_manager.update_table_schema(db_name, tbl_name, updated_cols)
    assert updated is True
    
    # Verify update
    updated_table = catalog_manager.get_table(db_name, tbl_name)
    assert len(updated_table["StorageDescriptor"]["Columns"]) == 4
    assert updated_table["StorageDescriptor"]["Columns"][3]["Name"] == "discount"
    
    # 4. Delete table
    deleted = catalog_manager.delete_table(db_name, tbl_name)
    assert deleted is True
    assert catalog_manager.get_table(db_name, tbl_name) is None
    
    # Cleanup database
    catalog_manager.delete_database(db_name)
