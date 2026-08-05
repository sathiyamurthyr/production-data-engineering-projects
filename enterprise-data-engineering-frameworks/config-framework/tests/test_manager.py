from config_framework.manager import ConfigManager
class TestConfig:
    def test_source(self):
        m=ConfigManager(); m.add_source("t",{"key":"val"}); assert m.get("key")=="val"
    def test_priority(self):
        m=ConfigManager(); m.add_source("low",{"k":"low"},priority=1); m.add_source("high",{"k":"high"},priority=10)
        assert m.get("k")=="high"
    def test_default(self):
        assert ConfigManager().get("x","def")=="def"
    def test_set(self):
        m=ConfigManager(); m.add_source("b",{"k":"base"}); m.set("k","override"); assert m.get("k")=="override"
    def test_file(self, tmp_path):
        f=tmp_path/"c.yaml"; f.write_text("key: file_val\n")
        m=ConfigManager(); m.add_file(f); assert m.get("key")=="file_val"
    def test_snapshot(self):
        m=ConfigManager(); m.add_source("t",{"a":1,"b":2}); assert m.snapshot()=={"a":1,"b":2}

