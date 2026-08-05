from lakehouse_framework.manager import *
class TestLakehouse:
    def test_write_read(self):
        t=LakehouseTable("orders"); v=t.write([{"id":1}])
        assert v==1 and len(t.read())==1
    def test_append(self):
        t=LakehouseTable("t"); t.write([{"id":1}]); t.write([{"id":2}])
        assert len(t.read())==2 and t.current_version==2
    def test_overwrite(self):
        t=LakehouseTable("t"); t.write([{"id":1}]); t.write([{"id":2}],mode="overwrite")
        assert len(t.read())==1
    def test_time_travel(self):
        t=LakehouseTable("t"); t.write([{"id":1}])
        r=t.time_travel(1); assert r["version"]==1
    def test_optimize(self):
        t=LakehouseTable("t"); t.write([{"id":1}]); r=t.optimize(); assert r["status"]=="success"
    def test_vacuum(self):
        t=LakehouseTable("t"); t.write([{"id":1}]); r=t.vacuum(); assert r["status"]=="success"
    def test_history(self):
        t=LakehouseTable("t"); t.write([{"id":1}]); t.write([{"id":2}])
        assert len(t.history())==2
    def test_manager(self):
        m=LakehouseManager(); m.create_table("orders")
        assert m.get_table("orders") is not None; assert "orders" in m.list_tables()

