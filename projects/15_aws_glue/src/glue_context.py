import sys
import logging
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("glue_context")

try:
    from pyspark.context import SparkContext
    from pyspark.sql import SparkSession
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from awsglue.utils import getResolvedOptions
    GLUE_ENVIRONMENT = True
except ImportError:
    GLUE_ENVIRONMENT = False
    logger.warning("AWS Glue libraries not found. Falling back to local PySpark session and mock GlueContext.")

class MockJob:
    """Mock implementation of the AWS Glue Job class for local testing."""
    def __init__(self, glue_context):
        self.glue_context = glue_context
        self.job_name = "MockGlueJob"
        logger.info("Initialized mock Glue Job.")

    def init(self, job_name: str, args: Dict[str, Any]):
        self.job_name = job_name
        logger.info(f"Mock Glue Job '{job_name}' initialized with arguments: {args}")

    def commit(self):
        logger.info("Mock Glue Job committed successfully.")


class MockGlueContext:
    """Mock implementation of the AWS Glue GlueContext class for local testing."""
    def __init__(self, spark_context):
        self.spark_context = spark_context
        self.spark_session = SparkSession.builder.getOrCreate()
        logger.info("Initialized mock GlueContext.")

    def write_dynamic_frame(self, frame, connection_options, format_options=None):
        logger.info(f"Writing Mock DynamicFrame to connection options: {connection_options}")
        # Return mock write result
        return frame

    def create_dynamic_frame_from_options(self, connection_type, connection_options, format_options=None, **kwargs):
        logger.info(f"Creating Mock DynamicFrame from options. connection_type={connection_type}, options={connection_options}")
        # In a mock environment, we can read local files using PySpark
        path = connection_options.get("paths", [None])[0]
        if path:
            # Handle standard local files for tests
            if connection_type == "s3" or path.startswith("file://") or "/" in path:
                df = self.spark_session.read.options(**(format_options or {})).csv(path, header=True, inferSchema=True)
                return MockDynamicFrame(df)
        return MockDynamicFrame(self.spark_session.createDataFrame([], {}))

    def create_dynamic_frame_from_catalog(self, database, table_name, **kwargs):
        logger.info(f"Creating Mock DynamicFrame from Catalog table {database}.{table_name}")
        # Return an empty mock dynamic frame
        return MockDynamicFrame(self.spark_session.createDataFrame([], {}))


class MockDynamicFrame:
    """Mock implementation of the AWS Glue DynamicFrame class for local testing."""
    def __init__(self, spark_df):
        self.spark_df = spark_df

    def toDF(self):
        return self.spark_df

    def show(self, num_rows=20):
        self.spark_df.show(num_rows)

    def printSchema(self):
        self.spark_df.printSchema()

    def count(self) -> int:
        return self.spark_df.count()

    def resolveChoice(self, choice=None, specs=None, **kwargs):
        logger.info(f"Mock DynamicFrame: resolving choices: {choice} {specs}")
        # Simple local implementation of type casting if specs are provided
        df = self.spark_df
        if specs:
            from pyspark.sql.functions import col
            for col_name, cast_type in specs:
                if cast_type == "double":
                    df = df.withColumn(col_name, col(col_name).cast("double"))
                elif cast_type == "int":
                    df = df.withColumn(col_name, col(col_name).cast("int"))
                elif cast_type == "string":
                    df = df.withColumn(col_name, col(col_name).cast("string"))
        return MockDynamicFrame(df)

    def dropNullFields(self, **kwargs):
        logger.info("Mock DynamicFrame: dropping null fields")
        # In PySpark, we can drop rows with all nulls or filter out completely null cols
        return MockDynamicFrame(self.spark_df.na.drop(how="all"))

    def selectFields(self, paths: List[str], **kwargs):
        logger.info(f"Mock DynamicFrame: selecting fields {paths}")
        existing_cols = [c for c in paths if c in self.spark_df.columns]
        return MockDynamicFrame(self.spark_df.select(*existing_cols))


def get_glue_context() -> tuple:
    """
    Initializes and returns SparkContext, GlueContext, and SparkSession.
    Uses fallback mocks if awsglue library is not available (i.e. local environment).
    """
    if GLUE_ENVIRONMENT:
        logger.info("Running in AWS Glue environment. Initializing native GlueContext.")
        sc = SparkContext.getOrCreate()
        glue_context = GlueContext(sc)
        spark_session = glue_context.spark_session
        return sc, glue_context, spark_session
    else:
        logger.info("Running in local environment. Initializing SparkSession and Mock GlueContext.")
        spark_session = SparkSession.builder \
            .appName("LocalGlueJob") \
            .master("local[*]") \
            .getOrCreate()
        sc = spark_session.sparkContext
        mock_glue_context = MockGlueContext(sc)
        return sc, mock_glue_context, spark_session


def get_job(glue_context) -> Any:
    """
    Initializes and returns a Glue Job instance (native or mock).
    """
    if GLUE_ENVIRONMENT:
        return Job(glue_context)
    else:
        return MockJob(glue_context)


def get_resolved_arguments(required_args: List[str], defaults: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Resolves job arguments. If running in AWS Glue, uses getResolvedOptions.
    If running locally, pulls from defaults or sys.argv parsing.
    """
    if GLUE_ENVIRONMENT:
        logger.info("Resolving arguments from Glue environment.")
        # AWS Glue adds standard prefix '--' to arguments
        args = getResolvedOptions(sys.argv, required_args)
        return args
    else:
        logger.info("Resolving arguments from local environment/defaults.")
        args = {}
        # Parse command line args like --JOB_NAME
        for arg in required_args:
            cli_arg = f"--{arg}"
            if cli_arg in sys.argv:
                idx = sys.argv.index(cli_arg)
                if idx + 1 < len(sys.argv):
                    args[arg] = sys.argv[idx + 1]
            elif defaults and arg in defaults:
                args[arg] = defaults[arg]
            else:
                args[arg] = "mock_value"
        return args
