"""
================================================================================
MODULE 41: Unit Testing with Pytest
================================================================================
1. EXPLANATION:
Pytest provides automated test discovery, assertions, and fixture management for pipeline code.

2. BUSINESS USE CASE:
Demonstrate clean unit test assertions.
"""
def add_amounts(a: float, b: float) -> float:
    return round(a + b, 2)

def test_add_amounts():
    assert add_amounts(10.50, 20.25) == 30.75

if __name__ == "__main__":
    test_add_amounts()
    print("Unit test passed.")
