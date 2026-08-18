# Enterprise Naming Standards

## Purpose

Define consistent naming conventions across all architectures.

## Naming Conventions

### Directories
- Lowercase, hyphen-separated: `payment-gateway/`
- Avoid abbreviations: `customer360/` not `c360/`

### Files
- Lowercase, hyphen-separated: `architecture-overview.md`
- Test files: `test_<module>.py`

### Resources
- Prefix with project name: `{project}-{type}-{environment}`
- Example: `payments-api-prod`

### Services
- Domain-based: `{domain}-{service}-{version}`
- Example: `payment-service-v1`

## Data Naming

### Tables
- snake_case: `customer_accounts`
- Plural nouns: `customers`, `transactions`

### Columns
- snake_case: `account_id`, `created_at`
- No prefixes: `id`, not `table_id`

### Kafka Topics
- Domain-based: `{domain}.{entity}.{event}`
- Example: `payment.transaction.completed`
