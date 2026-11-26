"""
S3 and EMRFS read/write optimization patterns for PySpark on EMR.
Provides code patterns for partition optimization, tuning partition size,
and boto3 script to cleanup aborted multi-part uploads to save costs.
Author: Sathiya Murthy (Data Engineering Diaries)
"""

import math
import logging
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError
from pyspark.sql import DataFrame
from pyspark.sql.functions import col

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("S3DataPatterns")


class S3Optimizer:
    """
    Utility class that details and configures optimized reads and writes between Amazon EMR and S3.
    """

    @staticmethod
    def get_emrfs_spark_configs() -> Dict[str, str]:
        """
        Returns recommended EMRFS and S3 performance configurations for PySpark.
        """
        return {
            # Enable EMRFS consistent view to prevent eventual consistency issues on older S3 buckets/regions
            "spark.hadoop.fs.s3.consistent": "true",
            "spark.hadoop.fs.s3.consistent.retryCount": "5",
            "spark.hadoop.fs.s3.consistent.retryPeriodSeconds": "10",
            
            # Fast upload configures multipart uploads to S3 directly from memory/local disk buffer
            "spark.hadoop.fs.s3a.fast.upload": "true",
            # Set multipart size to 100MB (optimizes memory vs network throughput)
            "spark.hadoop.fs.s3a.multipart.size": "104857600", 
            # Threshold to trigger multipart upload (100MB)
            "spark.hadoop.fs.s3a.multipart.threshold": "104857600",
            
            # Use DirectParquetOutputCommitter (specifically EmrOptimizedSparkSqlParquetOutputCommitter on EMR)
            # This bypasses the slow Hadoop default staging/renaming files on S3 which is highly inefficient
            "spark.sql.parquet.fs.optimized.committer.optimization-enabled": "true",
            "spark.sql.sources.commitProtocolClass": "com.amazon.ws.emr.hadoop.fs.EmrOptimizedSparkSqlParquetOutputCommitter"
        }

    @staticmethod
    def write_optimized_parquet(
        df: DataFrame,
        output_path: str,
        partition_cols: List[str],
        target_file_size_mb: int = 128,
        average_record_size_bytes: int = 250
    ) -> None:
        """
        Writes a PySpark DataFrame to S3 Parquet format, avoiding the 'small files problem'
        by calculating and applying the optimal repartition/coalesce size.
        
        :param df: Spark DataFrame to write.
        :param output_path: Destination S3 path.
        :param partition_cols: Columns to partition the output by.
        :param target_file_size_mb: Target size of each parquet file in MB (standard is 128MB).
        :param average_record_size_bytes: Est. size of a single row in memory/storage.
        """
        logger.info("Starting optimized write to %s", output_path)
        
        # Calculate total rows and estimate total data size
        total_rows = df.count()
        if total_rows == 0:
            logger.warning("Empty DataFrame, writing directly with minimal partitions.")
            df.write.mode("overwrite").parquet(output_path)
            return

        estimated_data_bytes = total_rows * average_record_size_bytes
        target_bytes = target_file_size_mb * 1024 * 1024
        
        # Calculate ideal number of files
        num_files = math.ceil(estimated_data_bytes / target_bytes)
        # Ensure we have at least 1 partition
        num_files = max(1, num_files)
        
        logger.info("Dataset statistics: total_rows=%d, estimated_size_mb=%.2fMB", 
                    total_rows, estimated_data_bytes / (1024 * 1024))
        logger.info("Target file size=%dMB, setting write parallelism (partitions) to %d", 
                    target_file_size_mb, num_files)

        # Repartitioning using columns + hash key ensures even partition sizing on disk
        # If partition count is small, coalesce() avoids full shuffle. Otherwise repartition() is safer.
        if num_files < df.rdd.getNumPartitions():
            writer_df = df.coalesce(num_files)
        else:
            # Repartition by partition columns to avoid cross-partition file fragmentation
            if partition_cols:
                writer_df = df.repartition(num_files, *[col(c) for c in partition_cols])
            else:
                writer_df = df.repartition(num_files)

        # Write out using Dynamic overwrite mode for updates
        writer = writer_df.write.mode("overwrite")
        if partition_cols:
            writer = writer.partitionBy(*partition_cols)
            
        writer.parquet(output_path)
        logger.info("Successfully finished writing optimized parquet files to %s", output_path)


class S3MultipartCleanup:
    """
    Cost management helper to abort stale multipart uploads in S3.
    """

    def __init__(self, region_name: str = "us-east-1"):
        self.s3_client = boto3.client("s3", region_name=region_name)

    def clean_aborted_multipart_uploads(self, bucket_name: str) -> int:
        """
        Aborts all incomplete multipart uploads on the target bucket.
        Incomplete uploads accumulate charges and remain hidden unless cleaned up.
        """
        logger.info("Scanning for aborted/incomplete multipart uploads in bucket: %s", bucket_name)
        aborted_count = 0
        try:
            paginator = self.s3_client.get_paginator("list_multipart_uploads")
            for page in paginator.paginate(Bucket=bucket_name):
                uploads = page.get("Uploads", [])
                for upload in uploads:
                    key = upload["Key"]
                    upload_id = upload["UploadId"]
                    logger.warning("Found aborted upload for Key: %s, UploadId: %s. Aborting...", key, upload_id)
                    
                    self.s3_client.abort_multipart_upload(
                        Bucket=bucket_name,
                        Key=key,
                        UploadId=upload_id
                    )
                    aborted_count += 1
                    
            logger.info("Cleanup completed. Total aborted uploads cleaned: %d", aborted_count)
            return aborted_count
        except ClientError as ce:
            logger.error("Failed to perform S3 multipart cleanup on bucket %s: %s", bucket_name, ce.response["Error"]["Message"])
            raise
