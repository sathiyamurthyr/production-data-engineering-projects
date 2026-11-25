"""
Unit tests for Lineage Tracker, Lineage Graph, and Lineage Reporter
"""

import pytest
from src.lineage.lineage_tracker import LineageTracker
from src.lineage.lineage_graph import LineageGraph
from src.lineage.lineage_reporter import LineageReporter

def test_lineage_tracker_recording():
    tracker = LineageTracker()
    edge = tracker.record_lineage(
        source_asset="raw_orders",
        target_asset="cleaned_orders",
        transformation_type="ETL_CLEAN",
        pipeline_name="order_pipeline",
    )
    
    assert edge.source_asset == "raw_orders"
    assert edge.target_asset == "cleaned_orders"
    assert len(tracker.get_all_edges()) == 1

def test_lineage_graph_traversal():
    tracker = LineageTracker()
    tracker.record_lineage("raw_cust", "bronze_cust", "COPY")
    tracker.record_lineage("bronze_cust", "silver_cust", "CLEAN")
    tracker.record_lineage("silver_cust", "gold_customer_360", "AGGREGATE")
    tracker.record_lineage("silver_cust", "gold_marketing_segments", "JOIN")
    
    graph = LineageGraph()
    graph.build_from_tracker(tracker)
    
    upstream = graph.get_upstream_dependencies("gold_customer_360")
    assert "silver_cust" in upstream
    assert "bronze_cust" in upstream
    assert "raw_cust" in upstream
    
    root_causes = graph.find_root_causes("gold_customer_360")
    assert root_causes == ["raw_cust"]
    
    downstream_impact = graph.get_downstream_impact("bronze_cust")
    assert "silver_cust" in downstream_impact
    assert "gold_customer_360" in downstream_impact
    assert "gold_marketing_segments" in downstream_impact

def test_lineage_cycle_detection():
    graph = LineageGraph()
    tracker = LineageTracker()
    tracker.record_lineage("node_a", "node_b", "ETL")
    tracker.record_lineage("node_b", "node_c", "ETL")
    tracker.record_lineage("node_c", "node_a", "INVALID_LOOP")
    graph.build_from_tracker(tracker)
    
    cycles = graph.detect_cycles()
    assert len(cycles) > 0

def test_lineage_reporter():
    tracker = LineageTracker()
    tracker.record_lineage("src_tbl", "dst_tbl", "SELECT")
    graph = LineageGraph()
    graph.build_from_tracker(tracker)
    
    reporter = LineageReporter(graph)
    mermaid_out = reporter.generate_mermaid_diagram()
    assert "graph LR" in mermaid_out
    assert "src_tbl" in mermaid_out
    assert "dst_tbl" in mermaid_out
    
    impact = reporter.generate_impact_report("src_tbl")
    assert impact["downstream_impacted_count"] == 1
    assert impact["risk_level"] in ("MEDIUM", "LOW")
