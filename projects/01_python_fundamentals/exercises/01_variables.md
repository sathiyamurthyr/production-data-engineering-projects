# Exercise 1: Variables and Data Types

## Easy

### Problem 1.1
Create variables to store the following data engineering configuration:
- Database host: "localhost"
- Database port: 5432
- Database name: "analytics"
- Maximum batch size: 10000
- Is production environment: False

**Solution**: See `solutions/01_variables.md`

---

### Problem 1.2
Write a function that determines the data type of a value and returns a human-readable string.

**Solution**: See `solutions/01_variables.md`

---

## Medium

### Problem 2.1
Create a configuration dictionary that stores ETL job parameters including:
- Source table name
- Target table name
- Batch size
- Last run timestamp
- Number of retries

**Solution**: See `solutions/01_variables.md`

---

## Hard

### Problem 3.1
Create a function that validates a configuration dictionary against a schema, ensuring:
- All required keys are present
- Values are of correct type
- Numeric values are within acceptable ranges

**Solution**: See `solutions/01_variables.md`