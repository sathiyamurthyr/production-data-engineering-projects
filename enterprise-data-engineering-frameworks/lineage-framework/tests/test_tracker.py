from lineage_framework.tracker import *
class TestLineage:
    def test_node_edge(self):
        t=LineageTracker(); n1=t.add_node(LineageNode(name="src")); n2=t.add_node(LineageNode(name="tgt"))
        t.add_edge(LineageEdge(n1,n2))
        assert t.get_upstream(n2)==[n1]; assert t.get_downstream(n1)==[n2]
    def test_impact(self):
        t=LineageTracker(); n1=t.add_node(LineageNode(name="s")); n2=t.add_node(LineageNode(name="m"))
        n3=t.add_node(LineageNode(name="e"))
        t.add_edge(LineageEdge(n1,n2)); t.add_edge(LineageEdge(n2,n3))
        imp=t.impact_analysis(n1); assert n2 in imp and n3 in imp
    def test_graph(self):
        t=LineageTracker(); n1=t.add_node(LineageNode(name="s")); n2=t.add_node(LineageNode(name="t"))
        t.add_edge(LineageEdge(n1,n2))
        g=t.lineage_graph(n2); assert g["upstream"][0].name=="s"

