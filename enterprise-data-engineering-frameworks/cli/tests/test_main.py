from cli.main import CLI
class TestCLI:
    def test_register(self):
        c=CLI(); c.command("test", lambda a: 0, "test command")
        assert "test" in c.list_commands()
    def test_run_help(self, capsys):
        c=CLI(); c.run(["--help"])
        out=capsys.readouterr().out; assert "Enterprise Data Engineering" in out
    def test_run_unknown(self, capsys):
        c=CLI(); r=c.run(["unknown"]); assert r==1
    def test_run_command(self, capsys):
        c=CLI(); c.command("hello", lambda a: 0, "say hello")
        r=c.run(["hello"]); assert r==0

