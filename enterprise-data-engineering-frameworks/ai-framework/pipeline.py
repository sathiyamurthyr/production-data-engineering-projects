"""AI framework: prompt registry, embeddings, vector store, retriever, agent SDK, eval, memory."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from shared.utils.helpers import generate_id, utc_now_iso

@dataclass
class Prompt:
    prompt_id: str=field(default_factory=lambda: generate_id("prompt_"))
    name: str=""; template: str=""; version: str="1.0.0"
    variables: list[str]=field(default_factory=list)

class PromptRegistry:
    def __init__(self): self._prompts={}
    def register(self, p): self._prompts[p.name]=p
    def get(self, name): return self._prompts.get(name)
    def render(self, prompt_name, **kwargs):
        p=self._prompts.get(prompt_name)
        if not p: raise ValueError(f"Prompt '{prompt_name}' not found")
        return p.template.format(**kwargs)

@dataclass
class Embedding:
    text: str; vector: list[float]; model: str="default"

class EmbeddingPipeline:
    def __init__(self, dim=128): self.dim=dim
    def embed(self, text):
        import hashlib
        h=hashlib.sha256(text.encode()).digest()
        vec=[(h[i%len(h)]/255.0-0.5)*2 for i in range(self.dim)]
        return Embedding(text=text, vector=vec, model="hash-based")
    def embed_batch(self, texts): return [self.embed(t) for t in texts]

class VectorStore:
    def __init__(self): self._vectors: list[Embedding]=[]
    def add(self, e): self._vectors.append(e)
    def search(self, query_vec, top_k=5):
        import math
        scored=[(e, sum(a*b for a,b in zip(query_vec,e.vector))/math.sqrt(sum(a*a for a in query_vec)*sum(b*b for b in e.vector)+1e-10)) for e in self._vectors]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    def clear(self): self._vectors.clear()
    @property
    def size(self): return len(self._vectors)

class Retriever:
    def __init__(self, store: VectorStore, embedder: EmbeddingPipeline): self.store=store; self.embedder=embedder
    def retrieve(self, query, top_k=5):
        qe=self.embedder.embed(query); return self.store.search(qe.vector, top_k)

@dataclass
class Message:
    role: str="user"; content: str=""; timestamp: str=field(default_factory=utc_now_iso)

class ConversationMemory:
    def __init__(self, max_messages=100): self._messages=[]; self._max=max_messages
    def add(self, role, content):
        self._messages.append(Message(role=role, content=content))
        if len(self._messages) > self._max: self._messages = self._messages[-self._max:]
    def get_history(self): return list(self._messages)
    def clear(self): self._messages.clear()

class Agent:
    def __init__(self, name, instructions=""): self.name=name; self.instructions=instructions; self.memory=ConversationMemory()
    def run(self, input_text):
        self.memory.add("user", input_text)
        response=f"Agent {self.name} processed: {input_text[:50]}"
        self.memory.add("assistant", response)
        return response

class EvaluationPipeline:
    def __init__(self): self._results=[]
    def evaluate(self, prediction, expected):
        score=1.0 if prediction==expected else 0.0
        self._results.append({"prediction":prediction,"expected":expected,"score":score})
        return score
    def average_score(self): return sum(r["score"] for r in self._results)/max(len(self._results),1)

