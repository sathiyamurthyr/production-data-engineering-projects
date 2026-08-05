from logging_framework.logger import StructuredLogger, set_correlation_id
class TestLogger:
    def test_info(self, capsys):
        StructuredLogger("t",level="INFO").info("hello")
        assert "hello" in capsys.readouterr().out
    def test_json(self, capsys):
        StructuredLogger("t",level="INFO",json_output=True).info("hello",key="val")
        import json; e=json.loads(capsys.readouterr().out.strip())
        assert e["message"]=="hello" and e["key"]=="val"
    def test_correlation(self, capsys):
        set_correlation_id("test-123")
        StructuredLogger("t",level="INFO",json_output=True).info("hello")
        import json; e=json.loads(capsys.readouterr().out.strip())
        assert e["correlation_id"]=="test-123"

