# Live FTA RX watch (real-world)

SkyCache does **not** replace SatDump. After a free-to-air weather pass:

1. SatDump writes PNG/JPG (or package dirs) to a products folder.
2. This service ingests new products into the local portal.

```bash
sudo cp skycache-rx-watch.service /etc/systemd/system/
# edit Environment= paths
sudo systemctl daemon-reload
sudo systemctl enable --now skycache-rx-watch.service
```

Manual one-shot:

```bash
skycache rx watch --dir /path/to/satdump/products --once
skycache rx log --satellite "NOAA 18" --elevation 42 --quality good
```

Legal: receive-only, unencrypted FTA / open amateur only. Not commercial broadband.
