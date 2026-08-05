from monitoring_framework.monitor import *
class TestMonitoring:
    def test_health(self):
        e=MonitoringEngine(); e.add_health_check(HealthCheck("db",lambda:True))
        r=e.run_health_checks(); assert len(r)==1 and r[0].healthy
    def test_health_fail(self):
        e=MonitoringEngine(); e.add_health_check(HealthCheck("db",lambda:(_ for _ in ()).throw(ValueError("down"))))
        r=e.run_health_checks(); assert not r[0].healthy and "down" in r[0].message
    def test_metrics(self):
        e=MonitoringEngine(); e.set_metric("cpu",45.5); assert e.get_metric("cpu")==45.5
    def test_alerts(self):
        e=MonitoringEngine(); a=e.raise_alert("high_cpu","critical","CPU>90%")
        assert len(e.get_alerts())==1; e.acknowledge_alert(a.alert_id)
        assert len(e.get_alerts(unack_only=True))==0

