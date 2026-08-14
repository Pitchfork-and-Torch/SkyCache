# Bit-rot verify schedule (local)

Weekly integrity check for open content packs. **No cloud.**

## systemd

```bash
sudo cp skycache-bitrot-verify.service skycache-bitrot-verify.timer /etc/systemd/system/
# edit data-dir path in the service if needed
sudo systemctl daemon-reload
sudo systemctl enable --now skycache-bitrot-verify.timer
systemctl list-timers | grep skycache
```

Or generate templates:

```bash
skycache bitrot install-templates --out /tmp/skycache-bitrot --data-dir /var/lib/skycache
```

## cron

See `skycache-bitrot.cron` example (Sunday 03:15).

## Manual

```bash
skycache skybrary doctor --verify --record
skycache ops status
```
