import logging
from datetime import datetime, timedelta
from src.orchestration.pipeline_config import PipelineConfig

# Try importing Airflow, otherwise mock it for non-airflow testing environments
try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False
    class DAG:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    class PythonOperator:
        def __init__(self, *args, **kwargs): pass
        def __rshift__(self, other): return other
        def __rrshift__(self, other): return self
        def __lshift__(self, other): return other
        def __rlshift__(self, other): return self

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Task wrapper functions
def run_extraction_orders():
    from src.ingestion.orders_extractor import OrdersExtractor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        extractor = OrdersExtractor(cfg)
        extractor.extract()
    monitor.log_run("orders_extractor", "SUCCESS", 15, t.duration)

def run_extraction_events():
    from src.ingestion.events_producer import EventsProducer
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        producer = EventsProducer(cfg)
        producer.produce()
    monitor.log_run("events_producer", "SUCCESS", 15, t.duration)

def run_extraction_catalog():
    from src.ingestion.product_catalog_loader import ProductCatalogLoader
    from src.ingestion.customer_api_extractor import CustomerAPIExtractor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        loader = ProductCatalogLoader(cfg)
        loader.load()
        extractor = CustomerAPIExtractor(cfg)
        extractor.extract()
    monitor.log_run("catalog_loader", "SUCCESS", 20, t.duration)

def run_bronze_orders():
    from src.bronze.bronze_orders import BronzeOrdersIngestor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    from src.monitoring.cost_tracker import CostTracker
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    cost = CostTracker(cfg)
    with Timer() as t:
        ingestor = BronzeOrdersIngestor(cfg)
        ingestor.ingest()
    monitor.log_run("bronze_orders", "SUCCESS", 15, t.duration)
    cost.track_run_cost("bronze_orders", t.duration, "spark")

def run_bronze_events():
    from src.bronze.bronze_events import BronzeEventsIngestor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    from src.monitoring.cost_tracker import CostTracker
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    cost = CostTracker(cfg)
    with Timer() as t:
        ingestor = BronzeEventsIngestor(cfg)
        ingestor.ingest()
    monitor.log_run("bronze_events", "SUCCESS", 15, t.duration)
    cost.track_run_cost("bronze_events", t.duration, "spark")

def run_bronze_catalog():
    from src.bronze.bronze_catalog import BronzeCatalogIngestor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    from src.monitoring.cost_tracker import CostTracker
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    cost = CostTracker(cfg)
    with Timer() as t:
        ingestor = BronzeCatalogIngestor(cfg)
        ingestor.ingest()
    monitor.log_run("bronze_catalog", "SUCCESS", 20, t.duration)
    cost.track_run_cost("bronze_catalog", t.duration, "spark")

def run_silver_orders():
    from src.silver.silver_orders import SilverOrdersProcessor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        processor = SilverOrdersProcessor(cfg)
        processor.process()
    monitor.log_run("silver_orders", "SUCCESS", 15, t.duration)

def run_silver_events():
    from src.silver.silver_events import SilverEventsProcessor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        processor = SilverEventsProcessor(cfg)
        processor.process()
    monitor.log_run("silver_events", "SUCCESS", 15, t.duration)

def run_silver_products():
    from src.silver.silver_products import SilverProductsProcessor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        processor = SilverProductsProcessor(cfg)
        processor.process()
    monitor.log_run("silver_products", "SUCCESS", 10, t.duration)

def run_silver_customers():
    from src.silver.silver_customers import SilverCustomersProcessor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        processor = SilverCustomersProcessor(cfg)
        processor.process()
    monitor.log_run("silver_customers", "SUCCESS", 10, t.duration)

def run_gold_date():
    from src.gold.gold_dim_date import GoldDimDateGenerator
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        generator = GoldDimDateGenerator(cfg)
        generator.generate()
    monitor.log_run("gold_dim_date", "SUCCESS", 365, t.duration)

def run_gold_products():
    from src.gold.gold_dim_products import GoldDimProductsProcessor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        processor = GoldDimProductsProcessor(cfg)
        processor.process()
    monitor.log_run("gold_dim_products", "SUCCESS", 10, t.duration)

def run_gold_customers():
    from src.gold.gold_dim_customers import GoldDimCustomersProcessor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        processor = GoldDimCustomersProcessor(cfg)
        processor.process()
    monitor.log_run("gold_dim_customers", "SUCCESS", 10, t.duration)

def run_gold_fact_orders():
    from src.gold.gold_fact_orders import GoldFactOrdersProcessor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        processor = GoldFactOrdersProcessor(cfg)
        processor.process()
    monitor.log_run("gold_fact_orders", "SUCCESS", 15, t.duration)

def run_gold_analytics():
    from src.gold.gold_marketing_metrics import GoldMarketingMetricsProcessor
    from src.gold.gold_sales_analytics import GoldSalesAnalyticsProcessor
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    with Timer() as t:
        mkt = GoldMarketingMetricsProcessor(cfg)
        mkt.process()
        sales = GoldSalesAnalyticsProcessor(cfg)
        sales.process()
    monitor.log_run("gold_analytics", "SUCCESS", 20, t.duration)

def run_serving_reports():
    from src.serving.report_generator import ExecutiveReportGenerator
    from src.serving.alerting import AlertingService
    from src.monitoring.pipeline_monitor import PipelineMonitor, Timer
    cfg = PipelineConfig()
    monitor = PipelineMonitor(cfg)
    alert = AlertingService()
    with Timer() as t:
        generator = ExecutiveReportGenerator(cfg)
        generator.generate_report()
        alert.send_slack_alert("Capstone Platform Execution Completed. Executive Report generated.", "INFO")
    monitor.log_run("report_generator", "SUCCESS", 3, t.duration)

# Airflow DAG Definition
default_args = {
    'owner': 'datamart_de_team',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 1),
    'email': ['oncall-de@datamart.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'datamart_global_capstone_pipeline',
    default_args=default_args,
    description='End-to-End ingestion, transformation, and analytics pipeline for DataMart Global',
    schedule_interval='@daily',
    catchup=False,
    tags=['production', 'capstone', 'datamart']
) as dag:

    task_extract_orders = PythonOperator(task_id='extract_orders', python_callable=run_extraction_orders)
    task_extract_events = PythonOperator(task_id='extract_events', python_callable=run_extraction_events)
    task_extract_catalog = PythonOperator(task_id='extract_catalog', python_callable=run_extraction_catalog)

    task_bronze_orders = PythonOperator(task_id='bronze_orders', python_callable=run_bronze_orders)
    task_bronze_events = PythonOperator(task_id='bronze_events', python_callable=run_bronze_events)
    task_bronze_catalog = PythonOperator(task_id='bronze_catalog', python_callable=run_bronze_catalog)

    task_silver_orders = PythonOperator(task_id='silver_orders', python_callable=run_silver_orders)
    task_silver_events = PythonOperator(task_id='silver_events', python_callable=run_silver_events)
    task_silver_products = PythonOperator(task_id='silver_products', python_callable=run_silver_products)
    task_silver_customers = PythonOperator(task_id='silver_customers', python_callable=run_silver_customers)

    task_gold_date = PythonOperator(task_id='gold_date', python_callable=run_gold_date)
    task_gold_products = PythonOperator(task_id='gold_products', python_callable=run_gold_products)
    task_gold_customers = PythonOperator(task_id='gold_customers', python_callable=run_gold_customers)
    task_gold_fact_orders = PythonOperator(task_id='gold_fact_orders', python_callable=run_gold_fact_orders)
    task_gold_analytics = PythonOperator(task_id='gold_analytics', python_callable=run_gold_analytics)

    task_serving_reports = PythonOperator(task_id='serving_reports', python_callable=run_serving_reports)

    # Define Workflow Dependencies
    task_extract_orders >> task_bronze_orders
    task_extract_events >> task_bronze_events
    task_extract_catalog >> task_bronze_catalog

    task_bronze_orders >> task_silver_orders
    task_bronze_events >> task_silver_events
    task_bronze_catalog >> [task_silver_products, task_silver_customers]

    task_silver_products >> task_gold_products
    task_silver_customers >> task_gold_customers
    task_gold_date 

    [task_silver_orders, task_gold_products, task_gold_customers, task_gold_date] >> task_gold_fact_orders

    [task_gold_fact_orders, task_silver_events] >> task_gold_analytics

    task_gold_analytics >> task_serving_reports
