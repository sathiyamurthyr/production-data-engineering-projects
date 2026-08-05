from file_framework.handler import *
class TestFile:
    def test_csv(self, tmp_path):
        h=CSVHandler(); p=tmp_path/"t.csv"; h.write(p, [{"n":"A"}])
        assert len(h.read(p))==1
    def test_json(self, tmp_path):
        h=JSONHandler(); p=tmp_path/"t.json"; h.write(p, [{"a":1}])
        assert len(h.read(p))==1
    def test_mgr(self, tmp_path):
        m=FileIngestionManager(); p=tmp_path/"t.csv"; m.write(p, [{"a":1}]); assert len(m.read(p))==1
    def test_unknown(self, tmp_path):
        import pytest; m=FileIngestionManager()
        with pytest.raises(ValueError): m.read(tmp_path/"t.xyz")

