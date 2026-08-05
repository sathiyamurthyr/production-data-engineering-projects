from ai_framework.pipeline import *
class TestAI:
    def test_prompt(self):
        r=PromptRegistry(); r.register(Prompt(name="greet",template="Hello {name}!",variables=["name"]))
        assert r.render("greet",name="World")=="Hello World!"
    def test_embedding(self):
        e=EmbeddingPipeline(64); emb=e.embed("hello")
        assert len(emb.vector)==64 and emb.text=="hello"
    def test_vector_store(self):
        e=EmbeddingPipeline(64); s=VectorStore()
        s.add(e.embed("hello world")); s.add(e.embed("goodbye world"))
        assert s.size==2
        results=s.search(e.embed("hello").vector, top_k=1); assert len(results)==1
    def test_retriever(self):
        e=EmbeddingPipeline(64); s=VectorStore()
        s.add(e.embed("Python programming")); s.add(e.embed("Data engineering"))
        r=Retriever(s,e); results=r.retrieve("Python", top_k=1); assert len(results)==1
    def test_memory(self):
        m=ConversationMemory(); m.add("user","hi"); m.add("assistant","hello")
        assert len(m.get_history())==2; m.clear(); assert len(m.get_history())==0
    def test_agent(self):
        a=Agent("test"); r=a.run("hello"); assert "test" in r and len(a.memory.get_history())==2
    def test_eval(self):
        ev=EvaluationPipeline(); ev.evaluate("A","A"); ev.evaluate("B","C")
        assert ev.average_score()==0.5

