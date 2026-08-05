from platform_sdk.generator import *
class TestPlatformSDK:
    def test_project_gen(self, tmp_path):
        g=ProjectGenerator(); g.register_template(ProjectTemplate(name="basic",files={"main.py":"print('hello')"}))
        r=g.generate("basic",str(tmp_path/"proj")); assert r["files"]==1
        assert (tmp_path/"proj/main.py").exists()
    def test_pipeline_gen(self):
        g=PipelineGenerator(); c=g.generate_etl("sales","csv","parquet")
        assert c["type"]=="etl" and "extract" in c["steps"]
    def test_config_gen(self):
        g=ConfigGenerator(); c=g.generate("test",db="postgres"); assert c["config"]["db"]=="postgres"
    def test_template(self):
        e=TemplateEngine(); e.register("greet","Hello {name}!")
        assert e.render("greet",name="World")=="Hello World!"

