# Solution 1: Variables and Data Types

## Easy

### Solution 1.1
```python
# Database configuration
db_host: str = "localhost"
db_port: int = 5432
db_name: str = "analytics"
max_batch_size: int = 10000
is_production: bool = False
```

### Solution 1.2
```python
def get_type_name(value) -> str:
    """Return human-readable type name."""
    type_map = {
        int: "Integer",
        float: "Float",
        str: "String",
        bool: "Boolean",
        list: "List",
        dict: "Dictionary",
        tuple: "Tuple",
        set: "Set",
        type(None): "None",
    }
    return type_map.get(type(value), "Unknown")
```

---

## Medium

### Solution 2.1
```python
etl_config: dict = {
    "source_table": "raw.customers",
    "target_table": "analytics.customers",
    "batch_size": 10000,
    "last_run": None,
    "retries": 3,
}
```

---

## Hard

### Solution 3.1
```python
def validate_config(config: dict, schema: dict) -> tuple[bool, list[str]]:
    """Validate configuration against schema."""
    errors = []

    for key, expected_type in schema.items():
        if key not in config:
            errors.append(f"Missing required key: {key}")
            continue

        if not isinstance(config[key], expected_type):
            errors.append(f"Key {key} has wrong type")

    # Validate batch size range
    if "batch_size" in config:
        if not 100 <= config["batch_size"] <= 100000:
            errors.append("Batch size must be between 100 and 100000")

    return len(errors) == 0, errors