from ingestion_framework.manager import *
class DummySource(IngestionSource):
    @property
    def name(self): return "dummy"
    def ingest(self): return [{"a":1},{"a":2}]
class TestIngestion:
    def test_ingest(self):
        m=IngestionManager(); m.register(DummySource())
        r=m.ingest("dummy"); assert r.status=="success" and r.records==2
    def test_not_found(self):
        assert IngestionManager().ingest("x").status=="failed"
    def test_all(self):
        m=IngestionManager(); m.register(DummySource())
        assert len(m.ingest_all())==1

