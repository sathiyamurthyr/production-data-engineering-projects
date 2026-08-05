# AI Framework

AI framework with prompt registry, embeddings, vector store, retriever, agent SDK, evaluation, and memory.

```python
from ai_framework.pipeline import PromptRegistry, Prompt, EmbeddingPipeline, VectorStore, Retriever, Agent
r=PromptRegistry(); r.register(Prompt(name='greet',template='Hello {name}!'))
e=EmbeddingPipeline(); s=VectorStore(); s.add(e.embed('hello'))
agent=Agent('assistant'); agent.run('What is data engineering?')
```
