from quality_framework.checks import *
class TestQuality:
    def test_schema(self):
        c=SchemaCheck({"name":str,"age":int})
        assert c.check([{"name":"A","age":30}]).passed
        assert not c.check([{"name":"A"}]).passed
    def test_completeness(self):
        c=CompletenessCheck(["name","email"])
        assert c.check([{"name":"A","email":"a@x"}]).passed
        assert not c.check([{"name":"A","email":None}]).passed
    def test_duplicates(self):
        c=DuplicateCheck(["id"])
        assert c.check([{"id":1},{"id":2}]).passed
        assert not c.check([{"id":1},{"id":1}]).passed
    def test_business_rule(self):
        c=BusinessRuleCheck(lambda r: r["age"]>=18)
        assert c.check([{"age":25}]).passed
        assert not c.check([{"age":15}]).passed
    def test_reporter(self):
        r=QualityReporter()
        r.run_checks([{"id":1,"name":"A"}], [DuplicateCheck(["id"]), CompletenessCheck(["name"])])
        assert r.all_passed() and r.overall_score()==1.0

