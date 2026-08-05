# Notification Framework

Multi-channel notifications: email, Slack, Teams, PagerDuty, webhooks.

```python
from notification_framework.notifier import NotificationEngine, ConsoleChannel
e=NotificationEngine(); e.register('console',ConsoleChannel()); e.send('console','Alert','Pipeline failed')
```
