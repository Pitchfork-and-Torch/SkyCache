SkyCache bit-rot schedule templates (local only).
1. Copy .service + .timer to /etc/systemd/system/
2. systemctl daemon-reload && systemctl enable --now skycache-bitrot-verify.timer
Or install the cron line under /etc/cron.d/
Legal: open packages only. Not commercial media integrity.
