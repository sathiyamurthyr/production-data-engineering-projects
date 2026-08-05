# Framework Core

The foundational framework providing plugin architecture, dependency injection, pipeline engine, retry engine, audit engine, validation engine, policy engine, storage abstraction, and extension SDK.

## Modules
- `plugin_manager.py` - Plugin registration, lifecycle, discovery
- `container.py` - DI with singleton/transient/scoped scopes
- `pipeline.py` - Pipeline execution with ordered steps, hooks, retry, conditions
- `retry.py` - Retry with fixed, linear, exponential, exponential-jitter backoff
- `audit.py` - Audit trail recording with file persistence and query
- `validation.py` - Schema, range validators with validation engine
- `policy.py` - Policy enforcement with priorities and conditions
- `storage.py` - Storage abstraction (local, in-memory, URI routing)
- `extension.py` - Extension SDK with dependency resolution

## Quick Start
```python
from framework_core import Pipeline, PipelineStep
pipeline = Pipeline("my_pipeline")
pipeline.add_step(PipelineStep("extract", extract_fn))
pipeline.add_step(PipelineStep("transform", transform_fn, depends_on=["extract"]))
result = pipeline.run()
```

