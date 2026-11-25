import uvicorn
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import pandas as pd
from src.orchestration.pipeline_config import PipelineConfig
from src.bronze import bronze_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DataMart Global Analytics API",
    description="Operational serving layer for serving Gold metrics and warehouse attributes.",
    version="1.0.0"
)

cfg = PipelineConfig()
gold_path = Path(cfg.storage_config.get("gold_path"))

def get_dataset_df(dataset_name: str) -> pd.DataFrame:
    """Helper function to load data from Gold storage using the fallback reader."""
    target_dir = gold_path / dataset_name
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_name} not found in storage.")
    
    df = bronze_utils.load_fallback_df(target_dir)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data files found for {dataset_name}.")
    return df

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected", "storage_layer": "available"}

@app.get("/api/v1/sales/summary")
def get_sales_summary() -> List[Dict[str, Any]]:
    try:
        df = get_dataset_df("sales_analytics/category_sales")
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error serving sales summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sales/daily")
def get_daily_sales() -> List[Dict[str, Any]]:
    try:
        df = get_dataset_df("sales_analytics/daily_sales")
        if "order_date" in df.columns:
            df["order_date"] = df["order_date"].astype(str)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error serving daily sales: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/marketing/metrics")
def get_marketing_metrics() -> List[Dict[str, Any]]:
    try:
        df = get_dataset_df("marketing_metrics")
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error serving marketing metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/customers/{customer_id}")
def get_customer_profile(customer_id: str) -> Dict[str, Any]:
    try:
        df = get_dataset_df("dim_customers")
        profile = df[df["customer_id"] == customer_id]
        if profile.empty:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")
        
        rec = profile.iloc[0].to_dict()
        for k, v in rec.items():
            if pd.api.types.is_datetime64_any_dtype(pd.Series([v])):
                rec[k] = str(v)
            elif pd.isna(v):
                rec[k] = None
        return rec
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error serving customer profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    api_cfg = cfg.api_config
    host = api_cfg.get("host", "0.0.0.0")
    port = api_cfg.get("port", 8000)
    logger.info(f"Starting FastAPI serving layer on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
