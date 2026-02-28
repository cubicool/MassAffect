# TODO

- [ ] Remove need to import parsers in `config.py`.
- [ ] Add a "name" field to non-autoload collectors.
- [ ] Experiment with adding additional id components to the "logs" namespace.
- [ ] What SHOULD happen when a Parser fails; will that `-> dict | None`?
- [ ] Improve logging SUBSTANTIALLY (always show class producing message, etc)
- [ ] Add log format string to `DebugTransport`.

# systemd Setup

Almost all of these commands will require root/sudo access.

## Copy, Reload, Start

```sh
cp massaffect-agent.service /etc/systemd/system/

systemctl daemon-reload
systemctl start massaffect-agent
```

## Enable At Boot

```sh
systemctl enable massaffect-agent
```

## Query Status

```sh
systemctl status massaffect-agent
```

## Query Logs

```sh
# Follow the current logs...
journalctl -u massaffect-agent -f

# Query startup errors...
journalctl -xeu massaffect-agent
```

## Restart (Code Changes)

```sh
systemctl restart massaffect-agent
```

## Restart (Server/systemd Changes)

```sh
systemctl daemon-reload
systemctl restart massaffect-agent
```
