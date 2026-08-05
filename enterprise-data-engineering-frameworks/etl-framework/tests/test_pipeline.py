from etl_framework.pipeline import *
class TestETL:
    def test_csv(self, tmp_path):
        f=tmp_path/"t.csv"; f.write_text("name,age\nA,30\nB,25\n")
        assert len(CSVExtractor(f).extract())==2
    def test_json(self, tmp_path):
        f=tmp_path/"t.json"; f.write_text('[{"a":1}]')
        assert len(JSONExtractor(f).extract())==1
    def test_loaders(self, tmp_path):
        assert CSVLoader(tmp_path/"o.csv").load([{"n":"A"}])==1
        assert JSONLoader(tmp_path/"o.json").load([{"a":1}])==1
        assert InMemoryLoader().load([{"a":1}])==1
    def test_transforms(self):
        assert len(drop_nulls("a")([{"a":1},{"a":None}]))==1
        assert add_field("b",2)([{"a":1}])[0]["b"]==2
        assert len(filter_records(lambda r:r["a"]>1)([{"a":1},{"a":2}]))==1
        assert len(deduplicate("id")([{"id":1},{"id":1},{"id":2}]))==2
    def test_scd(self):
        s=SCDType2("id",["name"]); r=s.apply([{"id":1,"name":"A"}])
        assert r[0]["version"]==1
        r=s.apply([{"id":1,"name":"B"}]); assert r[0]["version"]==2
        assert len(s.get_history(1))==2; assert len(s.get_current())==1
    def test_pipeline(self):
        l=InMemoryLoader()
        ETLPipeline("t").extract(ListExtractor([{"a":1},{"a":None}])).transform(drop_nulls("a")).load(l).run()
        assert len(l.data)==1

