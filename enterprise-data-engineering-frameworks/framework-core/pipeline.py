"""Pipeline execution engine with lifecycle hooks."""
from __future__ import annotations
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from shared.exceptions import PipelineError
from shared.utils.helpers import generate_id, utc_now_iso

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"

@dataclass
class StepResult:
    step_name: str
    status: StepStatus
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineResult:
    pipeline_id: str
    pipeline_name: str
    status: StepStatus
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    steps: list[StepResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    @property
    def is_success(self) -> bool:
        return self.status == StepStatus.SUCCESS
    @property
    def failed_steps(self) -> list[StepResult]:
        return [s for s in self.steps if s.status == StepStatus.FAILED]

class PipelineStep:
    def __init__(self, name: str, handler: Callable, depends_on: list[str] | None = None, retries: int = 0, timeout: float | None = None, condition: Callable | None = None) -> None:
        self.name = name
        self.handler = handler
        self.depends_on = depends_on or []
        self.retries = retries
        self.timeout = timeout
        self.condition = condition
    def execute(self, context: dict[str, Any]) -> StepResult:
        start = time.perf_counter()
        start_time = utc_now_iso()
        if self.condition and not self.condition(context):
            return StepResult(step_name=self.name, status=StepStatus.SKIPPED, start_time=start_time, end_time=utc_now_iso())
        attempts = 0
        last_error = None
        while attempts <= self.retries:
            try:
                output = self.handler(context)
                return StepResult(step_name=self.name, status=StepStatus.SUCCESS, start_time=start_time, end_time=utc_now_iso(), duration_seconds=time.perf_counter()-start, output=output)
            except Exception as e:
                last_error = str(e)
                attempts += 1
                if attempts <= self.retries:
                    time.sleep(min(2**attempts, 30))
        return StepResult(step_name=self.name, status=StepStatus.FAILED, start_time=start_time, end_time=utc_now_iso(), duration_seconds=time.perf_counter()-start, error=last_error)

class Pipeline:
    def __init__(self, name: str, steps: list[PipelineStep] | None = None) -> None:
        self.name = name
        self.steps = steps or []
        self._hooks: dict[str, list[Callable]] = {"pre_run": [], "post_run": [], "pre_step": [], "post_step": [], "on_error": [], "on_success": []}
    def add_step(self, step: PipelineStep) -> "Pipeline":
        self.steps.append(step)
        return self
    def add_hook(self, hook_name: str, callback: Callable) -> None:
        self._hooks.setdefault(hook_name, []).append(callback)
    def run(self, context: dict[str, Any] | None = None) -> PipelineResult:
        pipeline_id = generate_id("pipe_")
        ctx = context or {}
        ctx["pipeline_id"] = pipeline_id
        ctx["pipeline_name"] = self.name
        self._exec_hooks("pre_run", ctx)
        start = time.perf_counter()
        start_time = utc_now_iso()
        results: list[StepResult] = []
        all_success = True
        for step in self._ordered_steps():
            self._exec_hooks("pre_step", ctx, step)
            result = step.execute(ctx)
            results.append(result)
            ctx[step.name] = result.output
            self._exec_hooks("post_step", ctx, step, result)
            if result.status == StepStatus.FAILED:
                all_success = False
                self._exec_hooks("on_error", ctx, step, result)
                break
        elapsed = time.perf_counter() - start
        status = StepStatus.SUCCESS if all_success else StepStatus.FAILED
        pr = PipelineResult(pipeline_id=pipeline_id, pipeline_name=self.name, status=status, start_time=start_time, end_time=utc_now_iso(), duration_seconds=elapsed, steps=results)
        if all_success:
            self._exec_hooks("on_success", ctx, pr)
        self._exec_hooks("post_run", ctx, pr)
        return pr
    def _ordered_steps(self) -> list[PipelineStep]:
        step_map = {s.name: s for s in self.steps}
        ordered: list[PipelineStep] = []
        visited: set[str] = set()
        def visit(name: str) -> None:
            if name in visited:
                return
            step = step_map.get(name)
            if not step:
                raise PipelineError(f"Unknown dependency: {name}")
            visited.add(name)
            for dep in step.depends_on:
                visit(dep)
            ordered.append(step)
        for step in self.steps:
            visit(step.name)
        return ordered
    def _exec_hooks(self, hook_name: str, *args) -> None:
        for cb in self._hooks.get(hook_name, []):
            cb(*args)

