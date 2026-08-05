from streaming_framework.pipeline import *
class TestStreaming:
    def test_basic(self, tmp_path):
        s=ListSink(); p=StreamingPipeline("t",checkpoint_dir=str(tmp_path/"cp"))
        p.source(ListSource([{"id":i} for i in range(50)],batch_size=20)).sink(s)
        r=p.run(); assert r.total_records==50 and r.total_batches==3
    def test_transform(self, tmp_path):
        s=ListSink(); p=StreamingPipeline("t",checkpoint_dir=str(tmp_path/"cp"))
        p.source(ListSource([{"id":i,"v":i%2==0} for i in range(20)],batch_size=10)).transform(lambda b:[r for r in b if r["v"]]).sink(s)
        r=p.run(); assert r.total_records==10
    def test_max(self, tmp_path):
        s=ListSink(); p=StreamingPipeline("t",checkpoint_dir=str(tmp_path/"cp"),max_batches=2)
        p.source(ListSource([{"id":i} for i in range(100)],batch_size=20)).sink(s)
        r=p.run(); assert r.total_batches==2
    def test_cp(self, tmp_path):
        m=CheckpointManager(tmp_path/"cp"); m.save(Checkpoint("t",100,5))
        c=m.load("t"); assert c and c.offset==100
    def test_state(self):
        s=StateStore(); s.put("k","v"); assert s.get("k")=="v"
        s.delete("k"); assert s.get("k") is None
    def test_dlq(self):
        d=DeadLetterQueue(); d.write([{"e":"bad"}]); assert len(d.records)==1; d.clear(); assert len(d.records)==0

