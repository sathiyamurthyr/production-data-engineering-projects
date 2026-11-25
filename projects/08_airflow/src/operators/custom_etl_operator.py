"""
Operator: CustomETLOperator
===========================

PURPOSE:
    Custom enterprise BaseOperator subclass designed to execute a robust Extract-Transform-Load cycle
    from a REST API source into staged storage. Demonstrates standard operator development practices:
    `template_fields`, Jinja context rendering, Hook integration, XCom payload management, and error handling.

CONCEPTS COVERED:
    1. BaseOperator subclassing and constructor `super().__init__()` conventions
    2. `template_fields` definition for dynamic runtime rendering (Jinja support)
    3. `execute(context)` entrypoint lifecycle method
    4. Interacting with Airflow Hooks (`CustomApiHook` / `HttpHook`)
    5. Pushing clean, structured metadata dictionary to XCom for downstream consumption
    6. Raising `AirflowException` on unrecoverable failures

AUTHOR: Data Engineering Diaries
VERSION: 1.0.0
AIRFLOW: 2.9+
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, Optional, Sequence

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.utils.context import Context


class CustomETLOperator(BaseOperator):
    """
    Custom BaseOperator that extracts dataset records from an HTTP REST endpoint,
    transforms the raw records via an optional transformation function, and writes
    the output payload to a target staging path.

    Attributes:
        http_conn_id (str): Airflow Connection ID for the target API
        endpoint (str): API endpoint path (supports Jinja templating, e.g. `api/v1/orders/{{ ds }}`)
        output_path (str): File destination path (supports Jinja templating, e.g. `/tmp/orders_{{ ds_nodash }}.json`)
        transform_callable (Optional[Callable]): Optional Python function to map/clean raw items
        batch_size (int): Max records per API fetch page
        execution_date (str): Jinja templated execution date string
    """

    # Jinja-renderable operator fields
    template_fields: Sequence[str] = ("endpoint", "output_path", "execution_date")
    template_ext: Sequence[str] = (".sql", ".json")
    ui_color: str = "#e8f8f5"  # Light mint green background in UI graph view
    ui_fgcolor: str = "#000000"

    def __init__(
        self,
        *,
        http_conn_id: str,
        endpoint: str,
        output_path: str,
        transform_callable: Optional[Callable[[list[dict[str, Any]]], list[dict[str, Any]]]] = None,
        batch_size: int = 1000,
        execution_date: str = "{{ ds }}",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.http_conn_id = http_conn_id
        self.endpoint = endpoint
        self.output_path = output_path
        self.transform_callable = transform_callable
        self.batch_size = batch_size
        self.execution_date = execution_date

    def execute(self, context: Context) -> Dict[str, Any]:
        """
        Operator execution entrypoint called by worker process.

        Args:
            context (Context): Airflow execution context dictionary

        Returns:
            Dict[str, Any]: Metadata pushed to XCom key 'return_value'
        """
        self.log.info("Starting CustomETLOperator execution...")
        self.log.info("HTTP Connection ID : %s", self.http_conn_id)
        self.log.info("Endpoint           : %s", self.endpoint)
        self.log.info("Output Destination : %s", self.output_path)
        self.log.info("Execution Date     : %s", self.execution_date)

        start_time = time.time()

        try:
            # 1. Fetch data (In production, use CustomApiHook or HttpHook)
            # Example using CustomApiHook:
            # hook = CustomApiHook(http_conn_id=self.http_conn_id)
            # raw_records = hook.get_paginated_data(endpoint=self.endpoint, page_size=self.batch_size)

            # Simulated extraction payload
            raw_records = [
                {
                    "id": i + 1,
                    "date": self.execution_date,
                    "amount": 150.0 + (i * 12.5),
                    "currency": "USD",
                    "status": "COMPLETED",
                }
                for i in range(250)
            ]
            self.log.info("Extracted %d raw records from endpoint.", len(raw_records))

            # 2. Transform Phase
            if self.transform_callable:
                self.log.info("Applying custom transformation function...")
                transformed_records = self.transform_callable(raw_records)
            else:
                self.log.info("No transform function specified. Applying default schema formatting...")
                transformed_records = [
                    {
                        **item,
                        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "amount_cents": int(item["amount"] * 100),
                    }
                    for item in raw_records
                ]

            # 3. Write Phase to output destination
            os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(transformed_records, f, indent=2)

            file_size_bytes = os.path.getsize(self.output_path)
            duration_sec = round(time.time() - start_time, 3)

            self.log.info("Successfully wrote %d records to %s (%d bytes) in %.2fs",
                          len(transformed_records), self.output_path, file_size_bytes, duration_sec)

            # 4. Return Metadata Dictionary (Pushed to XCom)
            metadata = {
                "output_path": self.output_path,
                "raw_record_count": len(raw_records),
                "output_record_count": len(transformed_records),
                "file_size_bytes": file_size_bytes,
                "duration_seconds": duration_sec,
                "execution_date": self.execution_date,
            }
            return metadata

        except Exception as err:
            self.log.error("CustomETLOperator execution failed: %s", str(err), exc_info=True)
            raise AirflowException(f"CustomETLOperator failed to process endpoint '{self.endpoint}': {str(err)}") from err
