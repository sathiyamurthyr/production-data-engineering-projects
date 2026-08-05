from validation_framework.engine import *
class TestValidation:
    def test_required(self):
        c=DataContract("t").add_rule(ValidationRule("r","name","required"))
        assert c.validate({"name":"A"}).is_valid
        assert not c.validate({}).is_valid
    def test_type(self):
        c=DataContract("t").add_rule(ValidationRule("r","age","type",{"type":int}))
        assert c.validate({"age":30}).is_valid
        assert not c.validate({"age":"x"}).is_valid
    def test_min_max(self):
        c=DataContract("t").add_rule(ValidationRule("r","age","min",{"min":0})).add_rule(ValidationRule("r2","age","max",{"max":150}))
        assert c.validate({"age":25}).is_valid
        assert not c.validate({"age":-1}).is_valid
    def test_engine(self):
        e=ValidationEngine(); e.register_contract(DataContract("t").add_rule(ValidationRule("r","name","required")))
        assert e.validate("t",{"name":"A"}).is_valid

