"""Platform SDK: project generator, pipeline generator, config generator, template engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

@dataclass
class ProjectTemplate:
    name: str; description: str=""; files: dict[str,str]=field(default_factory=dict)

class ProjectGenerator:
    def __init__(self): self._templates={}
    def register_template(self, t): self._templates[t.name]=t
    def generate(self, template_name, output_dir):
        t=self._templates.get(template_name)
        if not t: raise ValueError(f"Template '{template_name}' not found")
        out=Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        for filepath, content in t.files.items():
            full=out/filepath; full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
        return {"template":template_name,"output":str(out),"files":len(t.files)}
    def list_templates(self): return list(self._templates.keys())

class PipelineGenerator:
    def generate_etl(self, name, source, target):
        return {"name":name,"type":"etl","source":source,"target":target,"steps":["extract","transform","load"]}
    def generate_streaming(self, name, source, target):
        return {"name":name,"type":"streaming","source":source,"target":target,"steps":["read","process","write"]}
    def to_yaml(self, config):
        import yaml; return yaml.dump(config, default_flow_style=False)

class ConfigGenerator:
    def generate(self, name, **kwargs):
        return {"name":name,"config":kwargs}
    def to_json(self, config): return json.dumps(config, indent=2)

class TemplateEngine:
    def __init__(self): self._templates={}
    def register(self, name, template): self._templates[name]=template
    def render(self, template_name, **kwargs):
        t=self._templates.get(template_name)
        if not t: raise ValueError(f"Template '{template_name}' not found")
        return t.format(**kwargs)

