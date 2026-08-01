# Solar / battery guidance (practical)

SkyCache is designed for **solar + battery** village/school hubs.

## Sizing sketch (starting point)

| Component | Starter | Notes |
|-----------|---------|--------|
| Panel | 40 - 100 W | More if live SDR + sun-poor season |
| Battery | 12 V LiFePO4 20 - 50 Ah | Prefer LiFePO4 over random Li-ion packs |
| Controller | PWM OK; MPPT better | Match panel V to controller |
| SBC load | ~3 - 8 W typical | Pi 4/5 + RTL-SDR + WiFi |
| Night mode | WiFi + portal only | Pause SDR in ECO power mode |

Rule of thumb: aim for **2× average daily consumption** in battery capacity for cloudy days.

## Wiring safety

- Fuse the battery positive close to the battery.
- Outdoor antenna coax: ground the mast; use a lightning plan appropriate to your region.
- Keep batteries in a ventilated, dry enclosure away from children.
- Label polarity. Use proper DC connectors (not loose twisted wire).

## Graceful degradation (software)

| SOC | Mode | Behavior |
|-----|------|----------|
| ≥ 40% | NORMAL | Live RX allowed + full portal |
| 20 - 40% | ECO | Pause live RX; serve cache |
| 10 - 20% | CRITICAL | WiFi portal only |
| &lt; 10% | EMERGENCY | Minimal services; pin emergency content |

Configure provider: `SKYCACHE_POWER_PROVIDER=mock|sysfs|ina219`.

## Monitoring

Phase 0 ships a **mock** battery gauge for demos. On laptops/SBCs with sysfs power_supply, try `sysfs`. INA219 I2C hooks are stubbed for Phase 3.
