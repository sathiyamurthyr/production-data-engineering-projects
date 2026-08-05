from observability_framework.system import *
class TestObservability:
    def test_sli(self):
        s=ObservabilitySystem(); s.record_sli(SLI("avail",SLIType.AVAILABILITY,0.999,0.99))
        assert s.get_sli("avail").value==0.999
    def test_slo(self):
        s=ObservabilitySystem(); s.define_slo(SLO("api",SLI("a",SLIType.AVAILABILITY),0.99,24,0.995))
        assert s.check_slo("api")
    def test_span(self):
        s=ObservabilitySystem(); sp=s.start_span("t1","db"); s.end_span(sp)
        assert len(s._spans)==1 and sp.end_time!=""
    def test_log(self):
        s=ObservabilitySystem(); s.log("INFO","test"); assert len(s._logs)==1
    def test_dashboard(self):
        s=ObservabilitySystem(); s.record_sli(SLI("lat",SLIType.LATENCY,50,100))
        d=s.get_dashboard_data(); assert "lat" in d["slis"]

