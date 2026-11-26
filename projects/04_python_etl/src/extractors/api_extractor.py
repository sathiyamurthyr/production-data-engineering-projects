"""
REST API Extractor module for fetching web API endpoints with retry logic.
"""

import time
from typing import Any, Dict, Optional
import requests
import pandas as pd

from src.extractors.base_extractor import BaseExtractor, ExtractionError


class APIExtractor(BaseExtractor):
    """Extractor for HTTP REST API endpoints with automatic exponential backoff."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize API Extractor.

        Config Keys:
            url (str): Endpoint URL.
            headers (dict, optional): HTTP Request Headers.
            params (dict, optional): Query parameters.
            timeout_seconds (int): Request timeout.
            max_retries (int): Retry attempts on transient errors.
            retry_delay_seconds (int): Base delay between retries.
            mock_response (dict, optional): Static payload for offline testing/mocking.
        """
        super().__init__(config)
        self.url = config.get("url", "")
        self.headers = config.get("headers", {})
        self.params = config.get("params", {})
        self.timeout = config.get("timeout_seconds", 10)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay_seconds", 2)
        self.mock_response = config.get("mock_response")

    def extract(self) -> pd.DataFrame:
        """
        Fetch data from the REST endpoint and format as pandas DataFrame.

        Returns:
            pd.DataFrame: Extracted JSON data flattened into a DataFrame.

        Raises:
            ExtractionError: If maximum retries are exceeded or response parsing fails.
        """
        if self.mock_response is not None:
            self.logger.info(f"Using mock response payload for API endpoint: {self.url or 'mock_url'}")
            return self._parse_json_response(self.mock_response)

        if not self.url:
            raise ExtractionError("API URL must be provided in extractor configuration.")

        attempts = 0
        while attempts < self.max_retries:
            attempts += 1
            try:
                self.logger.info(f"Fetching API endpoint (Attempt {attempts}/{self.max_retries}): {self.url}")
                response = requests.get(
                    self.url,
                    headers=self.headers,
                    params=self.params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                json_data = response.json()
                self.logger.info(f"API request succeeded with status code {response.status_code}")
                return self._parse_json_response(json_data)

            except (requests.RequestException, ValueError) as e:
                self.logger.warning(f"API request attempt {attempts} failed: {str(e)}")
                if attempts >= self.max_retries:
                    msg = f"API extraction failed after {self.max_retries} attempts for URL '{self.url}': {str(e)}"
                    self.logger.error(msg)
                    raise ExtractionError(msg) from e
                time.sleep(self.retry_delay * attempts)

        raise ExtractionError("Unexpected exit from retry loop in APIExtractor.")

    def _parse_json_response(self, data: Any) -> pd.DataFrame:
        """Helper to convert dictionary or list JSON response into DataFrame."""
        try:
            if isinstance(data, list):
                return pd.DataFrame(data)
            elif isinstance(data, dict):
                # Check common nested data keys like 'data', 'items', 'results'
                for key in ["data", "items", "results", "rates"]:
                    if key in data and isinstance(data[key], (list, dict)):
                        val = data[key]
                        if isinstance(val, dict):
                            # Flatten key-value dict (e.g. rates)
                            return pd.DataFrame([val])
                        return pd.DataFrame(val)
                # Fallback to single row dataframe
                return pd.DataFrame([data])
            else:
                raise ValueError(f"Unsupported JSON root type: {type(data)}")
        except Exception as e:
            raise ExtractionError(f"Failed to transform API JSON into DataFrame: {str(e)}") from e
