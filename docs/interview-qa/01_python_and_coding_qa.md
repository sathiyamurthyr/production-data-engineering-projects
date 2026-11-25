# 01. Python, Coding & General Foundations — Interview Q&A

---

### Q1: Coding — Check if a number divisible by 3 can be formed using all digits of an array
**Problem:** Given an integer array (e.g., `[40, 50, 90]`), determine whether all digits across its elements can be arranged to form a number divisible by 3.

**Key Insight:** A number is divisible by 3 if and only if the sum of all its digits is divisible by 3 (which is mathematically equivalent to `sum(arr) % 3 == 0`).

**Corrected Python Solution:**
```python
def is_divisible_by_3(arr: list[int]) -> bool:
    remainder = 0
    for num in arr:
        remainder = (remainder + num) % 3
    return remainder == 0


if __name__ == "__main__":
    arr = [40, 50, 90]
    print("Yes" if is_divisible_by_3(arr) else "No")  # Output: Yes (4+0+5+0+9+0 = 18)
```

---

### Q2: What is a Generator in Python, and why is it critical for Data Engineering?
**Answer:**
- A generator function uses `yield` instead of `return`, returning a lazy iterator object that produces one item at a time on demand.
- You do not need to manually implement `__iter__()` and `__next__()`.
- **Use case:** Streaming multi-GB log/CSV/JSON files where loading the whole file into memory would cause an Out-Of-Memory (OOM) crash.

```python
def first_n(n: int):
    num = 0
    while num < n:
        yield num
        num += 1

total = sum(first_n(1_000_000))  # O(1) memory
```

---

### Q3: What is the difference between a regular Function (`return`) and a Generator (`yield`)?
**Answer:**
| Aspect | Regular Function (`return`) | Generator (`yield`) |
|---|---|---|
| **Evaluation** | Eager — computes and stores all results in memory before returning | Lazy — yields one value at a time on demand |
| **Memory** | $O(N)$ for returning a list of $N$ items | $O(1)$ constant memory |
| **State** | Local variables are destroyed on `return` | Execution frame is paused and resumed across `next()` calls |

> **Interview Tip:** *"A function computes and returns all results eagerly; a generator uses `yield` to lazily stream values, making it ideal for large or unbounded data streams."*

---

### Q4: What are Decorators in Python? Give a Data Engineering example.
**Answer:**
A decorator is a design pattern that wraps an existing function or class using the `@decorator_name` syntax to add cross-cutting behavior (logging, timing, retries, auth checks) without modifying the underlying business logic.

```python
import functools
import time

def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.perf_counter() - start:.3f}s")
        return result
    return wrapper

@timeit
def run_etl():
    ...
```

---

### Q5: Compare Python `list`, `tuple`, `dict`, and `set` — when do you use each?
**Answer:**
| Collection | Syntax | Ordered | Mutable | Unique / Indexed | Best Data Engineering Use Case |
|---|---|---|---|---|---|
| **List** | `["apple", "banana"]` | Yes | Yes | Allows duplicates, index-based | Micro-batch buffers, ordered task lists |
| **Tuple** | `("apple", "banana")` | Yes | **No** | Allows duplicates, hashable if elements are | Immutable audit rows, config constants, dict keys |
| **Dict** | `{"brand": "Ford", "year": 1964}` | Insertion-ordered (3.7+) | Yes | Unique keys, $O(1)$ lookup | Hash joins, schema mappings, frequency counts, caches |
| **Set** | `{"apple", "banana"}` | Unordered | Yes | Unique elements, $O(1)$ lookup | Fast deduplication, set difference (`new - existing`) |

> **Interview Tip:** *"Use a `tuple` instead of a `list` when data should remain immutable (coordinates, DB records, constants) for safety and lower memory overhead. Use a `dict` for $O(1)$ key lookups, ID mapping, or caching."*

---

### Q6: What are Scala Traits, and how do they compare to interfaces?
**Answer:**
- Traits share interfaces and fields across classes in Scala (similar to Java interfaces + mixins).
- A trait can contain both **abstract** methods and **concrete (implemented)** methods.
- Classes and objects extend traits (`extends` / `with` for multiple traits), and traits cannot take constructor parameters or be instantiated directly.

---

### Q7: What TypeScript basics matter for full-stack Data Engineering / Foundry / Analytics UI work?
**Answer:**
- **Static Typing:** Catches schema/API payload mismatches at compile time (`string`, `number`, `boolean`, `interface`, `type`, union types like `"SUCCESS" | "FAILED"`).
- **Interfaces & Generics:** Define strict frontend contracts matching backend FastAPI/REST responses (`interface TransactionRecord { txnId: string; amount: number; }`).
- **Null Safety (`strictNullChecks`):** Forces explicit handling of `null` / `undefined` (`value?.field ?? fallback`), preventing runtime UI crashes on sparse data.

---

### Q8: How do you ensure Data Quality in Big Data projects?
**Answer:**
Validate, cleanse, and monitor data at every Medallion boundary:
1. **Schema & Type Enforcement:** Reject or quarantine malformed records at ingestion (`_corrupt_record` / DLQ).
2. **Profiling & Assertions:** Run automated completeness (nulls), uniqueness (PK duplicates), validity (regex/enums), and row-count/freshness checks.
3. **Observability:** Persist pass/fail metrics per `run_id` and alert on SLA/threshold breaches.

---

### Q9: What are the key challenges in processing Big Data in real time?
**Answer:**
1. **High Volume & Burst Backpressure:** Spikes overwhelming consumers (mitigated via Kafka partitioning, `maxOffsetsPerTrigger`, and autoscaling).
2. **Out-of-Order & Late-Arriving Data:** Handled via Event-Time processing and **Watermarks**.
3. **Exactly-Once & State Consistency:** Requires checkpointing + replayable sources + idempotent sinks (`MERGE` / transactions) plus scalable off-heap StateStores (RocksDB).

---

### Q10: How do you approach decision-making when leading a Data Engineering team?
**Answer:**
Balance technical architecture with business outcomes:
1. **Data-Driven Decisions:** Base architecture and optimization priorities on measured metrics (latency, cost, failure rate).
2. **Stakeholder Collaboration:** Align pipelines and SLAs closely with product, finance, and analytics owners.
3. **Risk Assessment:** Identify SPOFs, schema-drift risks, and rollback paths upfront.
4. **Agile Incremental Delivery:** Ship vertical slices (end-to-end Bronze → Gold for one domain) iteratively rather than big-bang rewrites.
5. **Mentorship:** Establish code reviews, testing standards, and runbooks to grow the team.
