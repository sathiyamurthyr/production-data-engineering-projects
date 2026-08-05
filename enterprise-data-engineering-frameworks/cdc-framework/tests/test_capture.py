from cdc_framework.capture import *
class TestCDC:
    def test_ts_initial(self):
        c=TimestampCDC("ts"); e=c.capture([{"id":1,"ts":"2026-01-01"}])
        assert len(e)==1 and e[0].change_type==ChangeType.INSERT
    def test_ts_incremental(self):
        c=TimestampCDC("ts"); c.capture([{"id":1,"ts":"2026-01-01"}])
        e=c.capture([{"id":1,"ts":"2026-01-01"},{"id":2,"ts":"2026-01-02"}])
        assert len(e)==1 and e[0].change_type==ChangeType.UPDATE
    def test_log(self):
        c=LogCDC(); e=c.capture([{"op":"insert","table":"t","data":{"id":1}}])
        assert len(e)==1 and c.position==1
    def test_processor(self):
        p=CDCProcessor()
        e=[ChangeEvent(ChangeType.INSERT,"t",{"id":1},position=1)]
        assert len(p.process(e))==1; assert len(p.process(e))==0

