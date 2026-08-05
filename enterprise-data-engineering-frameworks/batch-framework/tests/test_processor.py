from batch_framework.processor import BatchJob, BatchProcessor
class TestBatch:
    def test_simple(self):
        p=[]; proc=BatchProcessor("t").add_job(BatchJob("j",lambda d:p.extend(d)))
        r=proc.run([{"a":1},{"a":2}]); assert r[0].status=="success" and r[0].records==2 and len(p)==2
    def test_partitioned(self):
        proc=BatchProcessor("t").add_job(BatchJob("j",lambda d:None,partition_key="r"))
        r=proc.run([{"r":"US"},{"r":"EU"},{"r":"US"}]); assert r[0].records==3
    def test_fail(self):
        proc=BatchProcessor("t").add_job(BatchJob("j",lambda d:(_ for _ in ()).throw(ValueError("x"))))
        r=proc.run([{"a":1}]); assert r[0].status=="failed"

