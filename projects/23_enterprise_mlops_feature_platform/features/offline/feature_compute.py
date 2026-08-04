"""Feature Computation - Compute and materialize features."""

from datetime import datetime
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, window, avg, stddev, max, min, count, sum, lag, lead, datediff, months_between, current_date, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, TimestampType, BooleanType

from .feature_definitions import FeatureView, FeatureDefinition


class FeatureComputer:
    """Compute features from source data."""
    
    def __init__(self, spark: SparkSession):
        """Initialize feature computer.
        
        Args:
            spark: PySpark session
        """
        self.spark = spark
    
    def compute_feature_view(self, feature_view: FeatureView, as_of_date: datetime | None = None) -> DataFrame:
        """Compute all features in a feature view.
        
        Args:
            feature_view: Feature view to compute
            as_of_date: Point-in-time date for features
            
        Returns:
            DataFrame with all features
        """
        as_of_date = as_of_date or datetime.now()
        
        # Get base entity IDs
        entity_df = self._get_entity_ids(feature_view)
        
        # Compute each feature
        feature_dfs = []
        for feature in feature_view.features:
            feature_df = self._compute_feature(feature, as_of_date)
            feature_dfs.append(feature_df)
        
        # Join all features
        result = entity_df
        for feature_df in feature_dfs:
            result = result.join(feature_df, on=feature_view.entity_id, how="left")
        
        return result
    
    def _get_entity_ids(self, feature_view: FeatureView) -> DataFrame:
        """Get distinct entity IDs from source tables.
        
        Args:
            feature_view: Feature view
            
        Returns:
            DataFrame with entity IDs
        """
        # Get unique entity IDs from all source tables
        tables = set(f.source_table for f in feature_view.features)
        
        entity_ids = None
        for table in tables:
            df = self.spark.read.table(table).select(feature_view.entity_id).distinct()
            if entity_ids is None:
                entity_ids = df
            else:
                entity_ids = entity_ids.union(df)
        
        if entity_ids is None:
            # Create empty DataFrame with entity_id column
            entity_ids = self.spark.createDataFrame([], StructType([
                StructField(feature_view.entity_id, StringType(), True)
            ]))
        
        return entity_ids.distinct()
    
    def _compute_feature(self, feature: FeatureDefinition, as_of_date: datetime) -> DataFrame:
        """Compute a single feature.
        
        Args:
            feature: Feature definition
            as_of_date: Point-in-time date
            
        Returns:
            DataFrame with feature
        """
        # Read source table
        source_df = self.spark.read.table(feature.source_table)
        
        # Filter by timestamp for point-in-time correctness
        if feature.timestamp_col in source_df.columns:
            source_df = source_df.filter(col(feature.timestamp_col) <= as_of_date)
        
        # Apply transformation
        if feature.transformation.startswith("SELECT") or feature.transformation.startswith("WITH"):
            # SQL transformation
            feature_df = self._apply_sql_transformation(source_df, feature)
        else:
            # PySpark transformation
            feature_df = self._apply_pyspark_transformation(source_df, feature)
        
        # Select entity ID and feature value
        return feature_df.select(
            col(feature.entity_id),
            col(feature.name)
        )
    
    def _apply_sql_transformation(self, source_df: DataFrame, feature: FeatureDefinition) -> DataFrame:
        """Apply SQL transformation.
        
        Args:
            source_df: Source DataFrame
            feature: Feature definition
            
        Returns:
            Transformed DataFrame
        """
        # Register as temp view
        source_df.createOrReplaceTempView(f"source_{feature.name}")
        
        # Execute SQL
        sql = f"""
            SELECT 
                {feature.entity_id},
                {feature.transformation} AS {feature.name}
            FROM source_{feature.name}
            GROUP BY {feature.entity_id}
        """
        
        return self.spark.sql(sql)
    
    def _apply_pyspark_transformation(self, source_df: DataFrame, feature: FeatureDefinition) -> DataFrame:
        """Apply PySpark transformation.
        
        Args:
            source_df: Source DataFrame
            feature: Feature definition
            
        Returns:
            Transformed DataFrame
        """
        # This is a simplified version - in practice, you'd parse and execute the transformation
        if "COUNT" in feature.transformation and "OVER" in feature.transformation:
            # Window function
            return self._compute_window_feature(source_df, feature)
        elif "AVG" in feature.transformation or "SUM" in feature.transformation:
            # Aggregation
            return self._compute_aggregate_feature(source_df, feature)
        else:
            # Simple column selection
            return source_df.select(
                col(feature.entity_id),
                col(feature.transformation).alias(feature.name)
            )
    
    def _compute_window_feature(self, source_df: DataFrame, feature: FeatureDefinition) -> DataFrame:
        """Compute window-based feature.
        
        Args:
            source_df: Source DataFrame
            feature: Feature definition
            
        Returns:
            DataFrame with computed feature
        """
        from pyspark.sql.window import Window
        
        # Parse window specification
        # This is simplified - real implementation would parse the SQL
        partition_by = [feature.entity_id]
        order_by = [feature.timestamp_col]
        
        window_spec = Window.partitionBy(*partition_by).orderBy(*order_by)
        
        # Apply window function
        if "COUNT" in feature.transformation:
            result = source_df.withColumn(
                feature.name,
                count("*").over(window_spec.rowsBetween(-7, 0))
            )
        elif "AVG" in feature.transformation:
            result = source_df.withColumn(
                feature.name,
                avg("amount").over(window_spec.rowsBetween(-30, 0))
            )
        elif "STDDEV" in feature.transformation:
            result = source_df.withColumn(
                feature.name,
                stddev("amount").over(window_spec.rowsBetween(-30, 0))
            )
        else:
            result = source_df.withColumn(feature.name, col(feature.transformation))
        
        return result.select(feature.entity_id, feature.name).distinct()
    
    def _compute_aggregate_feature(self, source_df: DataFrame, feature: FeatureDefinition) -> DataFrame:
        """Compute aggregate feature.
        
        Args:
            source_df: Source DataFrame
            feature: Feature definition
            
        Returns:
            DataFrame with computed feature
        """
        # Group by entity and aggregate
        return source_df.groupBy(feature.entity_id).agg(
            avg(feature.transformation).alias(feature.name)
        )


class FeatureMaterializer:
    """Materialize features to offline store."""
    
    def __init__(self, spark: SparkSession, catalog_table: str):
        """Initialize feature materializer.
        
        Args:
            spark: PySpark session
            catalog_table: Target table in catalog
        """
        self.spark = spark
        self.catalog_table = catalog_table
    
    def materialize(self, features_df: DataFrame, partition_cols: list[str] = None) -> None:
        """Materialize features to Delta Lake.
        
        Args:
            features_df: Features DataFrame
            partition_cols: Columns to partition by
        """
        partition_cols = partition_cols or []
        
        # Write to Delta Lake with merge
        features_df.write.format("delta").mode("overwrite").partitionBy(*partition_cols).saveAsTable(self.catalog_table)
    
    def materialize_incremental(self, new_features_df: DataFrame, entity_id_col: str) -> None:
        """Materialize features incrementally using merge.
        
        Args:
            new_features_df: New features DataFrame
            entity_id_col: Entity ID column for merge
        """
        # Merge new features
        new_features_df.createOrReplaceTempView("new_features")
        
        merge_sql = f"""
            MERGE INTO {self.catalog_table} AS target
            USING new_features AS source
            ON target.{entity_id_col} = source.{entity_id_col}
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
        """
        
        self.spark.sql(merge_sql)


class FeatureValidator:
    """Validate feature quality using Great Expectations."""
    
    def __init__(self):
        """Initialize feature validator."""
        import great_expectations as ge
        self.ge = ge
    
    def validate_feature(self, df: DataFrame, feature: FeatureDefinition) -> dict[str, Any]:
        """Validate a feature against its validation rules.
        
        Args:
            df: Features DataFrame
            feature: Feature definition
            
        Returns:
            Validation results
        """
        # Convert to Great Expectations DataFrame
        ge_df = self.ge.from_pandas(df.toPandas())
        
        results = {
            "feature_name": feature.name,
            "success": True,
            "expectations": [],
        }
        
        # Apply validation rules
        for rule in feature.validation_rules:
            rule_type = rule.get("rule")
            
            if rule_type == "not_null":
                result = ge_df.expect_column_values_to_not_be_null(feature.name)
            elif rule_type == "range":
                result = ge_df.expect_column_values_to_be_between(
                    feature.name,
                    min_value=rule.get("min"),
                    max_value=rule.get("max")
                )
            elif rule_type == "unique":
                result = ge_df.expect_column_values_to_be_unique(feature.name)
            elif rule_type == "in_set":
                result = ge_df.expect_column_values_to_be_in_set(
                    feature.name,
                    value_set=rule.get("values")
                )
            else:
                continue
            
            results["expectations"].append({
                "rule": rule_type,
                "success": result.success,
                "details": result.result
            })
            
            if not result.success:
                results["success"] = False
        
        return results
    
    def validate_feature_view(self, df: DataFrame, feature_view: FeatureView) -> dict[str, Any]:
        """Validate all features in a feature view.
        
        Args:
            df: Features DataFrame
            feature_view: Feature view
            
        Returns:
            Validation results for all features
        """
        results = {
            "feature_view": feature_view.name,
            "features": [],
            "overall_success": True,
        }
        
        for feature in feature_view.features:
            feature_result = self.validate_feature(df, feature)
            results["features"].append(feature_result)
            
            if not feature_result["success"]:
                results["overall_success"] = False
        
        return results