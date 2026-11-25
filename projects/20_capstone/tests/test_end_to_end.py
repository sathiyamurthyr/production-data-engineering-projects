import pytest
from pathlib import Path
from src.orchestration.pipeline_config import PipelineConfig

def test_full_pipeline_end_to_end(test_config):
    """Executes the entire ingestion, bronze, silver, gold, and report generation pipeline."""
    # 1. Clear directories for clean execution
    storage_cfg = test_config.storage_config
    base_path = Path(storage_cfg.get("base_path"))
    
    # We don't delete landing to make sure extraction runs fine, but clear bronze/silver/gold
    for layer in ["bronze", "silver", "gold", "reports", "telemetry"]:
        dir_path = base_path / layer
        if dir_path.exists():
            import shutil
            shutil.rmtree(dir_path)

    # 2. Trigger Extraction Task wrappers
    from src.orchestration.capstone_dag import (
        run_extraction_orders,
        run_extraction_events,
        run_extraction_catalog,
        run_bronze_orders,
        run_bronze_events,
        run_bronze_catalog,
        run_silver_orders,
        run_silver_events,
        run_silver_products,
        run_silver_customers,
        run_gold_date,
        run_gold_products,
        run_gold_customers,
        run_gold_fact_orders,
        run_gold_analytics,
        run_serving_reports
    )

    logger_errors = []
    
    try:
        # Step 2.1 Extraction
        run_extraction_orders()
        run_extraction_events()
        run_extraction_catalog()
        
        # Step 2.2 Bronze Ingest
        run_bronze_orders()
        run_bronze_events()
        run_bronze_catalog()
        
        # Step 2.3 Silver Cleansing
        run_silver_orders()
        run_silver_events()
        run_silver_products()
        run_silver_customers()
        
        # Step 2.4 Gold modeling
        run_gold_date()
        run_gold_products()
        run_gold_customers()
        run_gold_fact_orders()
        run_gold_analytics()
        
        # Step 2.5 Serving Reports
        run_serving_reports()

    except Exception as e:
        logger_errors.append(str(e))
        pytest.fail(f"Pipeline crashed during execution: {e}")

    assert len(logger_errors) == 0

    # 3. Assert outputs exist and are non-empty
    assert (base_path / "bronze" / "orders").exists()
    assert (base_path / "silver" / "orders").exists()
    assert (base_path / "gold" / "fact_orders").exists()
    assert (base_path / "gold" / "sales_analytics" / "category_sales").exists()
    assert (base_path / "reports" / "executive_report.md").exists()
    assert (base_path / "telemetry" / "pipeline_runs.csv").exists()
    assert (base_path / "telemetry" / "platform_costs.csv").exists()
