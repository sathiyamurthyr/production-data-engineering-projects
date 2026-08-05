from secrets_framework.provider import *
from shared.exceptions import SecretError
import pytest
class TestSecrets:
    def test_env(self, monkeypatch):
        monkeypatch.setenv("TEST_SEC","val123"); assert EnvSecretProvider().get_secret("TEST_SEC")=="val123"
    def test_env_not_found(self):
        with pytest.raises(SecretError): EnvSecretProvider().get_secret("NONEXISTENT_12345")
    def test_inmemory(self):
        p=InMemorySecretProvider({"k":"v"}); assert p.get_secret("k")=="v"
    def test_manager_fallback(self):
        m=SecretsManager(); m.add_provider(InMemorySecretProvider({"a":"1"})); m.add_provider(InMemorySecretProvider({"b":"2"}))
        assert m.get_secret("a")=="1"; assert m.get_secret("b")=="2"
    def test_manager_not_found(self):
        with pytest.raises(SecretError): SecretsManager().get_secret("x")

