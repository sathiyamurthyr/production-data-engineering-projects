from governance_framework.governance import *
class TestGovernance:
    def test_access(self):
        e=GovernanceEngine(); e.add_access_policy(AccessPolicy("p1","table1","user1",AccessLevel.READ))
        assert e.check_access("user1","table1",AccessLevel.READ)
        assert not e.check_access("user2","table1",AccessLevel.READ)
    def test_admin(self):
        e=GovernanceEngine(); e.add_access_policy(AccessPolicy("p1","t1","u1",AccessLevel.ADMIN))
        assert e.check_access("u1","t1",AccessLevel.READ); assert e.check_access("u1","t1",AccessLevel.WRITE)
    def test_retention(self):
        e=GovernanceEngine(); e.add_retention_policy(RetentionPolicy("r1","orders",90))
        r=e.get_retention("orders"); assert r and r.retention_days==90
    def test_audit(self):
        e=GovernanceEngine(); e.audit("read","u1","t1")
        assert len(e.get_audit_trail())==1

