# Alert-bot for personal use

- Config .env:

Copy .env.example -> .env and config

- Run:

Install requirements, then:

```
python3 alert.py
```

- Can start as a service:

1. Copy alert-bot.service to /etc/systemd/system/

```
cp alert-bot.service /etc/systemd/system/
```

2. Install requirements (remember using sudo pip3 install, if you're not root)

3. Start service:

```
sudo systemctl start alert-bot
```
