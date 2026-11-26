import sys
import os
import logging

# Set PYTHONPATH to allow importing helper modules when running locally
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.glue_context import get_glue_context, get_job, get_resolved_arguments
from src.s3_integration import S3DataConnector
from src.dynamic_frame_ops import resolve_choices, drop_null_fields, select_fields, unnest_nested_fields
from src.data_quality_glue import GlueDataQualityEvaluator
from src.monitoring_glue import GlueJobMonitor

logger = logging.getLogger("glue_etl_job")

def run_etl():
    """
    Main ETL job execution routine.
    """
    # 1. Initialize AWS Glue/Spark Contexts
    sc, glue_context, spark_session = get_glue_context()
    job = get_job(glue_context)
    
    # Define required runtime arguments
    required_args = ["JOB_NAME", "raw_path", "processed_path", "sns_topic_arn"]
    default_args = {
        "JOB_NAME": "ecommerce_sales_etl",
        "raw_path": "s3://data-engineering-diaries-glue-demo/raw/sales/",
        "processed_path": "s3://data-engineering-diaries-glue-demo/processed/sales/",
        "sns_topic_arn": "arn:aws:sns:us-east-1:123456789012:GlueJobAlerts"
    }
    
    args = get_resolved_arguments(required_args, defaults=default_args)
    job.init(args["JOB_NAME"], args)
    
    monitor = GlueJobMonitor()
    
    try:
        logger.info(f"Starting Glue ETL Job execution: {args['JOB_NAME']}")
        
        # 2. Extract: Read Raw Sales Data from S3
        connector = S3DataConnector(glue_context)
        raw_dyf = connector.read_from_s3(
            s3_path=args["raw_path"],
            file_format="csv",
            format_options={"withHeader": "true", "separator": ","},
            use_bookmark=True
        )
        
        row_count = raw_dyf.count()
        logger.info(f"Loaded raw dataset containing {row_count} records.")
        monitor.publish_job_metric(args["JOB_NAME"], "RawRecordsLoaded", float(row_count))
        
        if row_count == 0:
            logger.warning("No new records to process. Committing bookmark and exiting.")
            job.commit()
            return

        # 3. Validate: Data Quality (DQDL) Rules Evaluation
        dq_rules = [
            "RowCount > 0",
            "ColumnExists \"order_id\"",
            "IsComplete \"order_id\"",
            "IsComplete \"customer_id\"",
            "ColumnDataType \"revenue\" = \"Double\"",
            "ColumnValues \"status\" in [\"completed\", \"pending\", \"cancelled\", \"refunded\"]"
        ]
        dq_evaluator = GlueDataQualityEvaluator(
            ruleset_name="sales_etl_quality_rules",
            dqdl_rules=dq_rules
        )
        
        dq_passed, dq_report, raw_dyf = dq_evaluator.evaluate(raw_dyf, glue_context)
        logger.info(f"Data Quality Report Summary: Passed={dq_passed}")
        for rule_status in dq_report:
            logger.info(f"Rule: {rule_status['Rule']} -> {rule_status['Status']} (Actual: {rule_status['ActualValue']})")
            
        if not dq_passed:
            alert_msg = f"Data Quality validation failed for job {args['JOB_NAME']}. Report:\n{str(dq_report)}"
            logger.error(alert_msg)
            monitor.send_sns_alert(
                topic_arn=args["sns_topic_arn"],
                subject=f"CRITICAL: Glue DQ Failure - {args['JOB_NAME']}",
                message=alert_msg
            )
            # Depending on business rules, we can raise an exception or proceed. Here we raise to abort pipeline.
            raise ValueError("ETL aborted due to Data Quality violations.")

        # 4. Transform: Clean and Schema Alignment
        # Cast column types
        schema_specs = [
            ("revenue", "cast:double"),
            ("discount", "cast:double"),
            ("order_id", "cast:string"),
            ("customer_id", "cast:string")
        ]
        transformed_dyf = resolve_choices(raw_dyf, specs=schema_specs)
        
        # Drop redundant Null rows/fields
        transformed_dyf = drop_null_fields(transformed_dyf)
        
        # Flatten nested data if present (CSV is flat, but run unnest to cover the interface requirement)
        transformed_dyf = unnest_nested_fields(transformed_dyf)
        
        # Prune columns to output selection
        output_fields = ["order_id", "customer_id", "order_date", "revenue", "status", "item_category", "region", "discount"]
        transformed_dyf = select_fields(transformed_dyf, fields=output_fields)
        
        # 5. Load: Write Processed Parquet Data Partitioned by Region
        connector.write_to_s3(
            dynamic_frame=transformed_dyf,
            s3_path=args["processed_path"],
            file_format="parquet",
            partition_keys=["region"],
            format_options={"compression": "snappy"}
        )
        
        # Publish success metrics
        monitor.publish_job_metric(args["JOB_NAME"], "ProcessedRecordsWritten", float(row_count))
        monitor.publish_job_metric(args["JOB_NAME"], "ETLSuccess", 1.0)
        
        # 6. Commit Job Bookmark State
        job.commit()
        logger.info(f"Glue ETL Job '{args['JOB_NAME']}' execution committed successfully.")

    except Exception as e:
        error_msg = f"Glue ETL Job '{args['JOB_NAME']}' failed with error: {str(e)}"
        logger.error(error_msg)
        monitor.publish_job_metric(args["JOB_NAME"], "ETLFailure", 1.0)
        monitor.send_sns_alert(
            topic_arn=args["sns_topic_arn"],
            subject=f"ALERT: Glue Job Execution Failure - {args['JOB_NAME']}",
            message=error_msg
        )
        raise e

if __name__ == "__main__":
    run_etl()
