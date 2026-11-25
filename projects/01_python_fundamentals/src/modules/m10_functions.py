"""
================================================================================
MODULE 10: Functions & Pure Functional Transformation
================================================================================
1. EXPLANATION:
Functions encapsulate reusable business logic. Pure functions (no side effects, same output for same input)
make ETL transformation steps deterministic and easy to unit test.

2. BUSINESS USE CASE:
Calculate net revenue after tax and discount using pure, deterministic functions.
"""
def compute_net_revenue(gross_amount: float, tax_rate: float = 0.10, discount: float = 0.0) -> float:
    """Compute net revenue: (gross - discount) * (1 + tax_rate)."""
    discounted = max(0.0, gross_amount - discount)
    net = discounted * (1.0 + tax_rate)
    return round(net, 2)

if __name__ == "__main__":
    print("Net Revenue:", compute_net_revenue(100.0, tax_rate=0.08, discount=10.0))
