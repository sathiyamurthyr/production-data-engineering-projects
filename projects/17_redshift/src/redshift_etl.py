"""
Redshift ETL Module
===================
Executes ELT workflows to move, merge (upsert), and transform data from raw
staging tables to clean production-grade dimension and fact tables in the core schema.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

class RedshiftETLPipeline:
    """
    Orchestrates staging-to-core database transfers using Redshift's recommended
    transactional MERGE/UPSERT pattern (staging table -> target table deletes -> insert -> analyze).
    """
    
    def __init__(self, db_conn: Any):
        self.conn = db_conn

    def run_sales_upsert(self) -> None:
        """
        Performs transactional UPSERT from staging.staging_sales into core.fact_sales.
        
        Steps:
        1. Open Transaction.
        2. Delete existing records from core.fact_sales where sales_id matches staging.
        3. Insert new/updated records from staging.staging_sales.
        4. Commit.
        5. Run ANALYZE on target table to update stats.
        6. TRUNCATE staging table to release blocks and reset for next batch.
        """
        logger.info("Starting UPSERT pipeline from staging.staging_sales to core.fact_sales...")
        
        # Redshift standard transaction upsert pattern
        upsert_queries = [
            "BEGIN TRANSACTION;",
            
            # Step 1: Delete matching records to prevent duplication
            """
            DELETE FROM core.fact_sales
            USING staging.staging_sales
            WHERE core.fact_sales.sales_id = staging.staging_sales.sales_id;
            """,
            
            # Step 2: Insert staging rows into fact table
            """
            INSERT INTO core.fact_sales (
                sales_id,
                customer_id,
                product_id,
                quantity,
                unit_price,
                discount,
                sale_date
            )
            SELECT 
                sales_id,
                customer_id,
                product_id,
                quantity,
                unit_price,
                discount,
                sale_date
            FROM staging.staging_sales;
            """,
            
            "COMMIT;"
        ]
        
        cursor = self.conn.cursor()
        try:
            for query in upsert_queries:
                logger.debug(f"Running ETL statement:\n{query}")
                cursor.execute(query)
            
            logger.info("UPSERT completed and committed successfully.")
            
            # Maintenance: Optimize stats on core table
            logger.info("Updating statistics on core.fact_sales...")
            cursor.execute("ANALYZE core.fact_sales;")
            
            # Cleanup: Clean staging table for next load
            logger.info("Truncating staging table staging.staging_sales...")
            cursor.execute("TRUNCATE staging.staging_sales;")
            self.conn.commit()
            
            logger.info("Sales ETL pipeline execution finished successfully.")
            
        except Exception as e:
            logger.error(f"ETL transaction failed: {e}. Executing rollback.")
            try:
                cursor.execute("ROLLBACK;")
            except Exception as rollback_err:
                logger.error(f"Rollback failed: {rollback_err}")
            raise e
        finally:
            cursor.close()

    def run_customer_upsert(self) -> None:
        """
        Performs transactional UPSERT from staging.staging_customers into core.dim_customer.
        """
        logger.info("Starting UPSERT pipeline from staging.staging_customers to core.dim_customer...")
        
        upsert_queries = [
            "BEGIN TRANSACTION;",
            
            """
            DELETE FROM core.dim_customer
            USING staging.staging_customers
            WHERE core.dim_customer.customer_id = staging.staging_customers.customer_id;
            """,
            
            """
            INSERT INTO core.dim_customer (
                customer_id,
                first_name,
                last_name,
                email,
                gender,
                country,
                signup_date,
                is_active
            )
            SELECT 
                customer_id,
                first_name,
                last_name,
                email,
                gender,
                country,
                signup_date,
                is_active
            FROM staging.staging_customers;
            """,
            
            "COMMIT;"
        ]
        
        cursor = self.conn.cursor()
        try:
            for query in upsert_queries:
                cursor.execute(query)
            logger.info("Customer UPSERT committed.")
            
            cursor.execute("ANALYZE core.dim_customer;")
            cursor.execute("TRUNCATE staging.staging_customers;")
            self.conn.commit()
            logger.info("Customer ETL pipeline completed.")
        except Exception as e:
            logger.error(f"Customer ETL pipeline failed: {e}. Rolling back.")
            cursor.execute("ROLLBACK;")
            raise e
        finally:
            cursor.close()
