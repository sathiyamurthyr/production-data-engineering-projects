"""
udf_examples.py
===============
Standard PySpark UDFs vs Vectorized Pandas UDFs (PyArrow) implementation and performance analysis.

Business Use Case:
    Applying custom Python business logic (e.g. email mask, complex financial risk score calculation,
    NLP sentiment categorization) that cannot easily be expressed using standard PySpark SQL functions.

Standard Python UDF vs Pandas UDF:
    - Standard UDF: Serializes each row out of JVM to Python worker process and back.
                    High serialization overhead, no vectorization, low performance.
    - Pandas UDF: Uses Apache Arrow for zero-copy memory transfer. Batches rows into
                  Pandas Series/DataFrame, enabling SIMD vectorization. Up to 100x faster!

Interview Questions:
    Q: Why should you avoid standard PySpark Python UDFs whenever possible?
    A: Python UDFs act as a black box to the Catalyst Optimizer (preventing predicate pushdown
       and code generation) and incur severe JVM-to-Python IPC serialization overhead. Always
       prefer built-in `pyspark.sql.functions` or Pandas UDFs.

    Q: How do Pandas UDFs achieve high performance in PySpark?
    A: Apache Arrow provides an in-memory columnar format shared between Java JVM and Python,
       eliminating expensive row-by-row serialization.

    Q: What are the main types of Pandas UDFs supported in PySpark 3.x?
    A: 1) Series to Series (Scalar Pandas UDF)
       2) Iterator of Series to Iterator of Series (Batch processing)
       3) Map (applyInPandas)
       4) Grouped Map (groupBy().applyInPandas())
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import pandas as pd
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.functions import pandas_udf, udf
from pyspark.sql.types import DoubleType, StringType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Standard Python UDF (Row-by-Row)
# ---------------------------------------------------------------------------

def mask_email_python(email: Optional[str]) -> Optional[str]:
    """
    Python function to obscure user email addresses (e.g. 'john.doe@gmail.com' -> 'j***e@gmail.com').
    """
    if not email or "@" not in email:
        return None
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


# Register standard UDF
mask_email_udf = udf(mask_email_python, StringType())


# ---------------------------------------------------------------------------
# 2. Vectorized Pandas UDF (PyArrow Batching)
# ---------------------------------------------------------------------------

@pandas_udf(DoubleType())
def calculate_discounted_price_pandas_udf(price_series: pd.Series, discount_pct_series: pd.Series) -> pd.Series:
    """
    Vectorized Pandas UDF to compute final discounted price using vectorized pandas arithmetic.

    Args:
        price_series: Pandas Series of unit prices.
        discount_pct_series: Pandas Series of discount percentages.

    Returns:
        Pandas Series of calculated discounted prices.
    """
    return (price_series * (1.0 - discount_pct_series / 100.0)).round(2)


@pandas_udf(StringType())
def categorize_customer_tier_pandas_udf(total_spend_series: pd.Series) -> pd.Series:
    """
    Vectorized tier classification using Pandas cut/conditions.
    """
    return pd.cut(
        total_spend_series,
        bins=[-1, 100, 500, 1000, float("inf")],
        labels=["Bronze", "Silver", "Gold", "Platinum"],
    ).astype(str)


# ---------------------------------------------------------------------------
# Application Functions
# ---------------------------------------------------------------------------

def apply_email_masking(df: DataFrame, email_col: str = "email") -> DataFrame:
    """
    Apply standard email masking UDF to a DataFrame.
    """
    logger.info("Applying standard Python UDF for email masking")
    return df.withColumn(f"{email_col}_masked", mask_email_udf(F.col(email_col)))


def apply_pandas_pricing_udf(df: DataFrame) -> DataFrame:
    """
    Apply vectorised Pandas UDF to calculate final price.
    """
    logger.info("Applying Vectorized Pandas UDF for discounted pricing")
    return df.withColumn(
        "discounted_price_udf",
        calculate_discounted_price_pandas_udf(F.col("unit_price"), F.col("discount_pct")),
    )


def register_sql_udfs(spark: SparkSession) -> None:
    """
    Register Python and Pandas UDFs for use in Spark SQL queries.
    """
    spark.udf.register("mask_email_sql", mask_email_python, StringType())
    spark.udf.register("calc_discount_pandas_sql", calculate_discounted_price_pandas_udf)
    logger.info("Registered UDFs in Spark SQL catalog")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.spark_session import get_spark
    from src.dataframe_basics import create_sample_sales

    spark = get_spark("UDFDemo")
    sales = create_sample_sales(spark)

    print("=== Vectorized Pandas UDF Output ===")
    sales_with_udf = apply_pandas_pricing_udf(sales)
    sales_with_udf.select("sale_id", "unit_price", "discount_pct", "total_amount", "discounted_price_udf").show()

    spark.stop()
