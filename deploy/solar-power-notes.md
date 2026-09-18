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

## Site Wh calibration (software)

```text
skycache power calibrate --battery-wh 240 --notes "12V 20Ah LiFePO4"
skycache power calibrate --battery-wh 100 --lab-default
```

Writes `data/ops/power-calibration.json`. Lab default (100 Wh) is software-complete. Replace it with the installed bank before a field weekend. Estimates stay order-of-magnitude.

## INA219 wiring (educational)

- Bus: 3.3 V I2C on the SBC (`SDA`/`SCL`). Default address often `0x40`.
- Sense the **load** side after the fuse, not the panel before the controller.
- Shunt must match expected current (village Pi + AP is usually well under 5 A).
- Confirm polarity and that the module is isolated from outdoor lightning paths.
- Software: `SKYCACHE_POWER_PROVIDER=ina219` after the bus enumerates. Until then use `sysfs` or `mock`.

## Monitoring

Lab demos use the **mock** gauge. On laptops/SBCs with sysfs power_supply, try `sysfs`. INA219 is optional field hardware - the calibration file is the software closer.
