"""
Data Enricher transformer for deriving metrics, calculated columns,
customer segmentation tiers, and currency adjustments.
"""

from typing import Any, Dict, Optional
import pandas as pd

from src.transformers.base_transformer import BaseTransformer, TransformationError


class DataEnricher(BaseTransformer):
    """Transformer that adds calculated metrics and domain enrichment logic."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Data Enricher.

        Config Keys:
            base_currency (str): Target base currency for monetary values.
            tax_rate (float): Tax rate decimal multiplier (e.g., 0.08 for 8%).
            customer_tier_thresholds (dict): Threshold amounts for VIP/Gold/Silver classification.
        """
        super().__init__(config)
        self.base_currency = config.get("base_currency", "USD")
        self.tax_rate = config.get("tax_rate", 0.08)
        self.tier_thresholds = config.get(
            "customer_tier_thresholds",
            {"vip": 5000.0, "gold": 1000.0, "silver": 200.0}
        )

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enrich input DataFrame with derived fields.

        Args:
            df: Input DataFrame.

        Returns:
            pd.DataFrame: Enriched DataFrame.

        Raises:
            TransformationError: If enrichment fails.
        """
        if df.empty:
            return df.copy()

        try:
            enriched_df = df.copy()

            # Enrich customer tiers if total_spent column exists
            if "total_spent" in enriched_df.columns:
                enriched_df["customer_tier"] = enriched_df["total_spent"].apply(
                    self._classify_customer_tier
                )
                self.logger.info("Enriched dataset with 'customer_tier' column.")

            # Calculate total item count and order subtotal if 'items' column exists (nested JSON orders)
            if "items" in enriched_df.columns:
                enriched_df["item_count"] = enriched_df["items"].apply(self._count_items)
                enriched_df["subtotal_amount"] = enriched_df["items"].apply(self._calc_items_subtotal)
                enriched_df["tax_amount"] = enriched_df["subtotal_amount"] * self.tax_rate
                enriched_df["grand_total"] = enriched_df["subtotal_amount"] + enriched_df["tax_amount"]
                self.logger.info("Enriched nested order line items with subtotal, tax, and grand_total.")

            # Calculate tax and total for dataset containing 'price' or 'unit_price' and 'quantity'
            elif "unit_price" in enriched_df.columns and "quantity" in enriched_df.columns:
                enriched_df["subtotal_amount"] = enriched_df["unit_price"] * enriched_df["quantity"]
                enriched_df["tax_amount"] = enriched_df["subtotal_amount"] * self.tax_rate
                enriched_df["grand_total"] = enriched_df["subtotal_amount"] + enriched_df["tax_amount"]
                self.logger.info("Calculated item line item totals.")

            # Add processed timestamp
            enriched_df["processed_at"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")

            return enriched_df

        except Exception as e:
            msg = f"Data enrichment failed: {str(e)}"
            self.logger.error(msg)
            raise TransformationError(msg) from e

    def _classify_customer_tier(self, amount: float) -> str:
        """Helper to classify spending tier."""
        try:
            val = float(amount)
        except (ValueError, TypeError):
            return "bronze"

        if val >= self.tier_thresholds.get("vip", 5000.0):
            return "vip"
        elif val >= self.tier_thresholds.get("gold", 1000.0):
            return "gold"
        elif val >= self.tier_thresholds.get("silver", 200.0):
            return "silver"
        return "bronze"

    @staticmethod
    def _count_items(items_list: Any) -> int:
        """Helper to count line items in order."""
        if isinstance(items_list, list):
            return sum(item.get("quantity", 1) if isinstance(item, dict) else 1 for item in items_list)
        return 0

    @staticmethod
    def _calc_items_subtotal(items_list: Any) -> float:
        """Helper to compute order subtotal from line items."""
        if isinstance(items_list, list):
            total = 0.0
            for item in items_list:
                if isinstance(item, dict):
                    qty = item.get("quantity", 1)
                    price = item.get("unit_price", item.get("price", 0.0))
                    total += qty * price
            return round(total, 2)
        return 0.0
