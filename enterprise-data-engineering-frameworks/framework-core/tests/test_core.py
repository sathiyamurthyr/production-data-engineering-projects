"""Tests for framework-core."""
import pytest
from framework_core.plugin_manager import Plugin, PluginManager
from framework_core.container import Container, Scope
from framework_core.pipeline import Pipeline, PipelineStep, StepStatus
from framework_core.retry import RetryEngine, RetryConfig
from framework_core.audit import AuditEngine
from framework_core.validation import SchemaValidator, RangeValidator, ValidationEngine
from framework_core.policy import Policy, PolicyEffect, PolicyEngine
from framework_core.storage import InMemoryStorage, StorageManager
from framework_core.extension import Extension, ExtensionManifest, ExtensionManager
from shared.exceptions import PluginError, ConfigurationError, RetryExhaustedError

class DummyPlugin(Plugin):
    @property
    def name(self) -> str: return "dummy"
    @property
    def version(self) -> str: return "1.0.0"
    def initialize(self, context: dict) -> None: self.initialized = True
    def shutdown(self) -> None: pass

class Service:
    def __init__(self, value: int = 0) -> None: self.value = value

class DummyExt(Extension):
    @property
    def manifest(self) -> ExtensionManifest: return ExtensionManifest(name="dummy", version="1.0.0")
    def install(self, context: dict) -> None: self.installed = True
    def uninstall(self) -> None: self.installed = False

class TestPluginManager:
    def test_register_get(self):
        mgr = PluginManager(); p = DummyPlugin(); mgr.register(p); assert mgr.get("dummy") is p
    def test_duplicate(self):
        mgr = PluginManager(); mgr.register(DummyPlugin())
        with pytest.raises(PluginError): mgr.register(DummyPlugin())
    def test_unregister(self):
        mgr = PluginManager(); p = DummyPlugin(); mgr.register(p); mgr.unregister("dummy"); assert mgr.get("dummy") is None

class TestContainer:
    def test_resolve(self):
        c = Container(); c.register(Service, Service); assert isinstance(c.resolve(Service), Service)
    def test_singleton(self):
        c = Container(); c.register(Service, Service, scope=Scope.SINGLETON); assert c.resolve(Service) is c.resolve(Service)
    def test_transient(self):
        c = Container(); c.register(Service, Service, scope=Scope.TRANSIENT); assert c.resolve(Service) is not c.resolve(Service)
    def test_factory(self):
        c = Container(); c.register_factory(Service, lambda c: Service(value=99)); assert c.resolve(Service).value == 99
    def test_circular(self):
        c = Container(); c.register_factory(Service, lambda c: c.resolve(Service))
        with pytest.raises(ConfigurationError): c.resolve(Service)

class TestPipeline:
    def test_simple(self):
        p = Pipeline("t"); p.add_step(PipelineStep("a", lambda ctx: 1))
        p.add_step(PipelineStep("b", lambda ctx: ctx["a"]+1, depends_on=["a"])); r = p.run()
        assert r.is_success and r.steps[1].output == 2
    def test_failure(self):
        p = Pipeline("t"); p.add_step(PipelineStep("f", lambda ctx: (_ for _ in ()).throw(ValueError("x")))); r = p.run()
        assert r.status == StepStatus.FAILED
    def test_skip(self):
        p = Pipeline("t"); p.add_step(PipelineStep("s", lambda ctx: 1, condition=lambda ctx: False)); r = p.run()
        assert r.steps[0].status == StepStatus.SKIPPED
    def test_retry(self):
        attempts = []
        def flaky(ctx):
            attempts.append(1)
            if len(attempts) < 3: raise ValueError("retry")
            return "ok"
        p = Pipeline("t"); p.add_step(PipelineStep("flaky", flaky, retries=3)); r = p.run()
        assert r.is_success and len(attempts) == 3

class TestRetry:
    def test_success(self): assert RetryEngine(RetryConfig(max_attempts=3)).execute(lambda: 42) == 42
    def test_exhausted(self):
        with pytest.raises(RetryExhaustedError):
            RetryEngine(RetryConfig(max_attempts=2, initial_delay=0.01)).execute(lambda: (_ for _ in ()).throw(ValueError("x")))

class TestAudit:
    def test_record_query(self):
        e = AuditEngine(); e.record("access", "u1", "read", "t1")
        assert len(e.query(actor="u1")) == 1 and len(e.query(actor="u2")) == 0

class TestValidation:
    def test_schema(self):
        v = SchemaValidator({"name": str, "age": int})
        assert v.validate({"name": "A", "age": 30}).is_valid
        assert not v.validate({"name": "A"}).is_valid
    def test_range(self):
        v = RangeValidator(0, 100); assert v.validate(50).is_valid; assert not v.validate(-1).is_valid
    def test_engine(self):
        eng = ValidationEngine(); eng.register("age", RangeValidator(0, 150)); assert eng.validate("age", 25).is_valid

class TestPolicy:
    def test_default_deny(self):
        assert PolicyEngine(default_effect=PolicyEffect.DENY).evaluate("read", "t").effect == PolicyEffect.DENY
    def test_matching(self):
        eng = PolicyEngine(default_effect=PolicyEffect.DENY)
        eng.add_policy(Policy(name="a", effect=PolicyEffect.ALLOW, actions=["read"], resources=["t1"]))
        assert eng.evaluate("read", "t1").effect == PolicyEffect.ALLOW
    def test_conditions(self):
        eng = PolicyEngine(default_effect=PolicyEffect.DENY)
        eng.add_policy(Policy(name="admin", effect=PolicyEffect.ALLOW, conditions=[lambda ctx: ctx.get("role")=="admin"]))
        assert eng.evaluate("read", "t", {"role": "admin"}).effect == PolicyEffect.ALLOW
        assert eng.evaluate("read", "t", {"role": "user"}).effect == PolicyEffect.DENY

class TestStorage:
    def test_inmemory(self):
        s = InMemoryStorage(); s.write("a.txt", b"hello"); assert s.read("a.txt") == b"hello"
        assert s.exists("a.txt"); s.delete("a.txt"); assert not s.exists("a.txt")
    def test_manager(self):
        mgr = StorageManager(); mgr.write("memory://t.txt", b"hello"); assert mgr.read("memory://t.txt") == b"hello"

class TestExtension:
    def test_install_uninstall(self):
        mgr = ExtensionManager(); ext = DummyExt(); mgr.install(ext)
        assert ext.installed and mgr.get("dummy") is ext
        mgr.uninstall("dummy"); assert mgr.get("dummy") is None

