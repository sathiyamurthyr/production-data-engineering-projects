import logging
from typing import List, Tuple, Any

logger = logging.getLogger("dynamic_frame_ops")

try:
    from awsglue.dynamicframe import DynamicFrame
    GLUE_ENVIRONMENT = True
except ImportError:
    GLUE_ENVIRONMENT = False

def resolve_choices(dynamic_frame: Any, specs: List[Tuple[str, str]]) -> Any:
    """
    Resolves data types of columns in a DynamicFrame using cast rules.
    Example: specs = [("revenue", "cast:double"), ("order_id", "cast:string")]
    """
    logger.info(f"Resolving schema choices with specs: {specs}")
    if GLUE_ENVIRONMENT and isinstance(dynamic_frame, DynamicFrame):
        # Native Glue resolveChoice
        return dynamic_frame.resolveChoice(specs=specs)
    else:
        # Fallback PySpark logic (MockDynamicFrame or PySpark DataFrame)
        logger.info("Applying mock or local Spark resolveChoice mapping.")
        # If it's a wrapper, unpack it
        is_wrapper = hasattr(dynamic_frame, "spark_df")
        df = dynamic_frame.spark_df if is_wrapper else dynamic_frame
        
        from pyspark.sql.functions import col
        for column_name, choice_action in specs:
            # parsing "cast:double" -> "double"
            cast_type = choice_action.split(":")[-1] if ":" in choice_action else choice_action
            if cast_type == "double":
                df = df.withColumn(column_name, col(column_name).cast("double"))
            elif cast_type == "int" or cast_type == "integer":
                df = df.withColumn(column_name, col(column_name).cast("integer"))
            elif cast_type == "string":
                df = df.withColumn(column_name, col(column_name).cast("string"))
            elif cast_type == "float":
                df = df.withColumn(column_name, col(column_name).cast("float"))
        
        if is_wrapper:
            from src.glue_context import MockDynamicFrame
            return MockDynamicFrame(df)
        return df

def drop_null_fields(dynamic_frame: Any) -> Any:
    """
    Removes columns from the DynamicFrame that contain only null values.
    """
    logger.info("Dropping null fields from DynamicFrame.")
    if GLUE_ENVIRONMENT and isinstance(dynamic_frame, DynamicFrame):
        return dynamic_frame.dropNullFields()
    else:
        logger.info("Applying mock/local Spark dropNullFields.")
        is_wrapper = hasattr(dynamic_frame, "spark_df")
        df = dynamic_frame.spark_df if is_wrapper else dynamic_frame
        
        # Calculate non-null counts for each column
        total_rows = df.count()
        if total_rows == 0:
            return dynamic_frame
            
        columns_to_keep = []
        for col_name in df.columns:
            # If the column has at least one non-null value, we keep it
            non_null_count = df.filter(df[col_name].isNotNull()).count()
            if non_null_count > 0:
                columns_to_keep.append(col_name)
                
        df_filtered = df.select(*columns_to_keep)
        if is_wrapper:
            from src.glue_context import MockDynamicFrame
            return MockDynamicFrame(df_filtered)
        return df_filtered

def unnest_nested_fields(dynamic_frame: Any) -> Any:
    """
    Flattens nested structures (StructType) in the DynamicFrame.
    Example: struct_col.sub_field becomes struct_col_sub_field.
    """
    logger.info("Unnesting (flattening) nested columns in DynamicFrame.")
    if GLUE_ENVIRONMENT and isinstance(dynamic_frame, DynamicFrame):
        return dynamic_frame.unnest()
    else:
        logger.info("Applying local Spark unnest (flattening) logic.")
        is_wrapper = hasattr(dynamic_frame, "spark_df")
        df = dynamic_frame.spark_df if is_wrapper else dynamic_frame
        
        from pyspark.sql.types import StructType
        
        def flatten_df(nested_df):
            flat_cols = []
            nested_occurred = False
            for field in nested_df.schema.fields:
                if isinstance(field.dataType, StructType):
                    nested_occurred = True
                    for subfield in field.dataType.fields:
                        flat_cols.append(
                            f"`{field.name}`.`{subfield.name}` as `{field.name}_{subfield.name}`"
                        )
                else:
                    flat_cols.append(f"`{field.name}`")
            if nested_occurred:
                return flatten_df(nested_df.selectExpr(*flat_cols))
            return nested_df

        df_flat = flatten_df(df)
        if is_wrapper:
            from src.glue_context import MockDynamicFrame
            return MockDynamicFrame(df_flat)
        return df_flat

def select_fields(dynamic_frame: Any, fields: List[str]) -> Any:
    """
    Selects a subset of fields from a DynamicFrame.
    """
    logger.info(f"Selecting fields: {fields}")
    if GLUE_ENVIRONMENT and isinstance(dynamic_frame, DynamicFrame):
        return dynamic_frame.select_fields(paths=fields)
    else:
        logger.info("Applying mock/local Spark select_fields.")
        is_wrapper = hasattr(dynamic_frame, "spark_df")
        df = dynamic_frame.spark_df if is_wrapper else dynamic_frame
        
        # Keep only the fields that actually exist in the schema
        valid_fields = [f for f in fields if f in df.columns]
        df_selected = df.select(*valid_fields)
        
        if is_wrapper:
            from src.glue_context import MockDynamicFrame
            return MockDynamicFrame(df_selected)
        return df_selected
