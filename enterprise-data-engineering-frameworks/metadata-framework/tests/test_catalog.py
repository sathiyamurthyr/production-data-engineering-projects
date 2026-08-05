from metadata_framework.catalog import *
class TestMetadata:
    def test_table(self):
        c=MetadataCatalog(); c.register_table(TableMetadata(name="users",owner="t1"))
        assert c.get_table("users") is not None; assert c.get_table("x") is None
    def test_tag(self):
        c=MetadataCatalog(); c.register_table(TableMetadata(name="t1",tags=["pii"]))
        c.register_table(TableMetadata(name="t2",tags=["public"]))
        assert len(c.list_tables("pii"))==1
    def test_search(self):
        c=MetadataCatalog(); c.register_table(TableMetadata(name="orders",description="Order data"))
        assert len(c.search_tables("order"))==1
    def test_contract(self):
        c=MetadataCatalog(); c.register_contract(DataContract(name="users_contract"))
        assert c.get_contract("users_contract") is not None

