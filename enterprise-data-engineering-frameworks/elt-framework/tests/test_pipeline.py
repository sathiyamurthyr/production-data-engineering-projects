from elt_framework.pipeline import ELTModel, ELTPipeline
class TestELT:
    def test_run(self):
        p=ELTPipeline("t"); p.add_model(ELTModel("s","SELECT 1")); p.add_model(ELTModel("m","SELECT * FROM s",depends_on=["s"]))
        r=p.run(); assert r["models"]==2
    def test_order(self):
        p=ELTPipeline("t"); p.add_model(ELTModel("m","x",depends_on=["s"])); p.add_model(ELTModel("s","y"))
        assert p._order()[0].name=="s"

