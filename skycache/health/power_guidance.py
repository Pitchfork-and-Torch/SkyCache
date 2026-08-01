"""Power UX guidance: time-to-ECO estimates and printable maintainer sheets.

Honest estimates only - real drain depends on radio load, temperature, and
battery chemistry. Designed for solar village nodes (2 - 4 GB SBCs).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from skycache.models import PowerMode

# Approximate board draw (watts) by power mode - conservative Pi-class + AP
# Used only for human guidance, not hard control loops.
MODE_DRAW_W: dict[str, float] = {
    PowerMode.NORMAL.value: 6.5,  # portal + optional RX + mesh
    PowerMode.ECO.value: 4.0,  # no live RX
    PowerMode.CRITICAL.value: 2.8,  # portal only
    PowerMode.EMERGENCY.value: 1.8,  # minimal
}

# Default battery capacity if operator has not configured one (Wh)
DEFAULT_BATTERY_WH = 100.0  # ~12V 8Ah class small UPS / solar bank

# SOC thresholds matching mode_from_soc
SOC_ECO = 40.0
SOC_CRITICAL = 20.0
SOC_EMERGENCY = 10.0


def hours_until_threshold(
    percent: float | None,
    *,
    target_percent: float,
    battery_wh: float = DEFAULT_BATTERY_WH,
    draw_w: float | None = None,
    mode: PowerMode | str | None = None,
    on_ac: bool | None = None,
) -> dict[str, Any]:
    """Estimate hours until SOC reaches target_percent while discharging.

    Returns structured guidance; never claims precision beyond order-of-magnitude.
    """
    if on_ac is True:
        return {
            "hours": None,
            "reachable": False,
            "reason": "on_ac_or_charging",
            "message": "On AC/solar charge - not draining toward ECO.",
            "estimate_quality": "n/a",
        }
    if percent is None:
        return {
            "hours": None,
            "reachable": False,
            "reason": "soc_unknown",
            "message": "Battery percent unknown - connect sysfs/INA219 or set mock for lab.",
            "estimate_quality": "none",
        }
    if percent <= target_percent:
        return {
            "hours": 0.0,
            "reachable": True,
            "reason": "already_at_or_below",
            "message": f"Already at or below {target_percent:.0f}% SOC.",
            "estimate_quality": "exact",
        }

    mode_s = mode.value if isinstance(mode, PowerMode) else (mode or PowerMode.NORMAL.value)
    watts = float(draw_w if draw_w is not None else MODE_DRAW_W.get(str(mode_s), 5.0))
    if watts <= 0:
        watts = 5.0
    wh_available = battery_wh * max(0.0, (percent - target_percent) / 100.0)
    hours = wh_available / watts
    return {
        "hours": round(hours, 1),
        "reachable": True,
        "reason": "discharging_estimate",
        "message": (
            f"Roughly {hours:.1f} h until ~{target_percent:.0f}% SOC "
            f"(~{battery_wh:.0f} Wh pack, ~{watts:.1f} W draw). Order-of-magnitude only."
        ),
        "estimate_quality": "rough",
        "assumptions": {
            "battery_wh": battery_wh,
            "draw_w": watts,
            "from_percent": percent,
            "to_percent": target_percent,
            "mode": str(mode_s),
        },
    }


def power_guidance(
    percent: float | None,
    mode: PowerMode | str,
    *,
    on_ac: bool | None = None,
    battery_wh: float = DEFAULT_BATTERY_WH,
) -> dict[str, Any]:
    """Full operator guidance block for API / doctor / printable sheet."""
    mode_s = mode.value if isinstance(mode, PowerMode) else str(mode)
    to_eco = hours_until_threshold(
        percent,
        target_percent=SOC_ECO,
        battery_wh=battery_wh,
        mode=mode_s,
        on_ac=on_ac,
    )
    to_critical = hours_until_threshold(
        percent,
        target_percent=SOC_CRITICAL,
        battery_wh=battery_wh,
        mode=mode_s,
        on_ac=on_ac,
    )
    to_emergency = hours_until_threshold(
        percent,
        target_percent=SOC_EMERGENCY,
        battery_wh=battery_wh,
        mode=mode_s,
        on_ac=on_ac,
    )
    tips: list[str] = []
    if on_ac is not True and percent is not None and percent < 50:
        tips.append("Reduce live RX and mesh TX if sun is weak; prefer USB mule.")
    if mode_s == PowerMode.ECO.value:
        tips.append("ECO: live RX disabled. Portal and cached content stay up.")
    if mode_s in {PowerMode.CRITICAL.value, PowerMode.EMERGENCY.value}:
        tips.append("Conserve power: serve emergency/health only; pause gateway pulls.")
    if on_ac is True:
        tips.append("Charging path OK - keep solar / AC healthy before night.")

    return {
        "percent": percent,
        "mode": mode_s,
        "on_ac": on_ac,
        "battery_wh_assumed": battery_wh,
        "thresholds": {
            "eco_percent": SOC_ECO,
            "critical_percent": SOC_CRITICAL,
            "emergency_percent": SOC_EMERGENCY,
        },
        "hours_until_eco": to_eco,
        "hours_until_critical": to_critical,
        "hours_until_emergency": to_emergency,
        "mode_draw_w": MODE_DRAW_W,
        "tips": tips,
        "honest": (
            "Estimates are rough. Measure your bank (Wh) and site load for field accuracy. "
            "Nodes fail from power ignorance more often than from software."
        ),
    }


def maintainer_power_sheet_html(
    guidance: dict[str, Any],
    *,
    node_id: str = "",
    hotspot_ssid: str = "SkyCache-Local",
    version: str = "",
) -> str:
    """Printable HTML sheet for wall-mount next to the node (no heavy PDF deps)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pct = guidance.get("percent")
    mode = guidance.get("mode") or "?"
    eco = guidance.get("hours_until_eco") or {}
    crit = guidance.get("hours_until_critical") or {}
    tips = guidance.get("tips") or []
    tip_li = "".join(f"<li>{_esc(t)}</li>" for t in tips) or "<li>No special tips.</li>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>SkyCache power maintainer sheet</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 42rem; margin: 1.5rem auto;
         color: #0f172a; line-height: 1.45; }}
  h1 {{ font-size: 1.35rem; margin-bottom: 0.25rem; }}
  .meta {{ color: #475569; font-size: 0.9rem; margin-bottom: 1rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 0.5rem 0.65rem; text-align: left; }}
  th {{ background: #f1f5f9; }}
  .warn {{ background: #fef3c7; }}
  .foot {{ font-size: 0.85rem; color: #64748b; margin-top: 1.5rem; }}
  @media print {{ body {{ margin: 0.5in; }} .noprint {{ display: none; }} }}
</style>
</head>
<body>
  <p class="noprint"><button onclick="window.print()">Print sheet</button></p>
  <h1>SkyCache power sheet</h1>
  <p class="meta">Node {_esc(node_id or "(unset)")}  |  SSID {_esc(hotspot_ssid)}  | 
     printed {now}{_esc(f"  |  v{version}" if version else "")}</p>
  <table>
    <tr><th>Battery SOC</th><td>{_esc(str(pct) if pct is not None else "unknown")}%</td></tr>
    <tr><th>Mode now</th><td>{_esc(str(mode))}</td></tr>
    <tr class="warn"><th>Hours until ECO (~40%)</th>
        <td>{_esc(str(eco.get("hours") if eco.get("hours") is not None else eco.get("message", " - ")))}</td></tr>
    <tr><th>Hours until CRITICAL (~20%)</th>
        <td>{_esc(str(crit.get("hours") if crit.get("hours") is not None else crit.get("message", " - ")))}</td></tr>
  </table>
  <h2>Maintainer actions</h2>
  <ul>{tip_li}
    <li>Check solar panel clean + cable strain weekly.</li>
    <li>Confirm portal loads on hub Wi-Fi after any power event.</li>
    <li>Disaster: keep emergency/health packs; export USB mule before battery dies.</li>
  </ul>
  <h2>Mode guide</h2>
  <table>
    <tr><th>Mode</th><th>SOC</th><th>Behavior</th></tr>
    <tr><td>NORMAL</td><td>≥40%</td><td>Full portal; live RX allowed</td></tr>
    <tr><td>ECO</td><td>20 - 40%</td><td>No live RX; portal + mesh cache</td></tr>
    <tr><td>CRITICAL</td><td>10 - 20%</td><td>Portal only; pause heavy pulls</td></tr>
    <tr><td>EMERGENCY</td><td>&lt;10%</td><td>Minimal service; protect critical content</td></tr>
  </table>
  <p class="foot">{_esc(str(guidance.get("honest") or ""))}</p>
  <p class="foot">Not free commercial broadband. Store-and-forward knowledge hub only.</p>
</body>
</html>
"""


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
