from notification_framework.notifier import *
class TestNotification:
    def test_console(self, capsys):
        e=NotificationEngine(); e.register("console",ConsoleChannel())
        assert e.send("console","Test","Hello") is True
        assert "Hello" in capsys.readouterr().out
    def test_unknown(self):
        e=NotificationEngine(); assert e.send("x","T","B") is False
    def test_broadcast(self, capsys):
        e=NotificationEngine(); e.register("console",ConsoleChannel())
        r=e.broadcast("T","B"); assert all(r.values())
    def test_history(self, capsys):
        e=NotificationEngine(); e.register("console",ConsoleChannel())
        e.send("console","T","B"); assert len(e.get_history())==1

