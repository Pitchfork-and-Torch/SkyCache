from skycache.health.power import MockPowerProvider, mode_from_soc, should_run_live_rx
from skycache.models import PowerMode


def test_mode_thresholds():
    assert mode_from_soc(90) == PowerMode.NORMAL
    assert mode_from_soc(35) == PowerMode.ECO
    assert mode_from_soc(15) == PowerMode.CRITICAL
    assert mode_from_soc(5) == PowerMode.EMERGENCY
    assert mode_from_soc(None) == PowerMode.NORMAL


def test_live_rx_gated():
    assert should_run_live_rx(PowerMode.NORMAL)
    assert not should_run_live_rx(PowerMode.ECO)


def test_mock_provider():
    p = MockPowerProvider(42)
    assert p.battery_percent() == 42
