import pytest

from qate_env.configurator import Configurator, GatewayConfig, GatewayMode


def test_production_gateway_requires_a_config_key():
    with pytest.raises(ValueError, match="requires config_key"):
        GatewayConfig(GatewayMode.PROD, None)


def test_simulator_gateway_refuses_a_config_key():
    with pytest.raises(ValueError, match="cannot have config_key"):
        GatewayConfig(GatewayMode.SIMULATOR, "DEFAULT")


def test_no_gateway_refuses_a_config_key():
    with pytest.raises(ValueError, match="cannot have config_key"):
        GatewayConfig(GatewayMode.NONE, "DEFAULT")


def test_valid_gateway_configs():
    assert GatewayConfig(GatewayMode.PROD, "DEFAULT").config_key == "DEFAULT"
    assert GatewayConfig(GatewayMode.SIMULATOR, None).config_key is None
    assert GatewayConfig(GatewayMode.NONE, None).config_key is None


def test_none_mode_never_sets_up_a_gateway(monkeypatch):
    class Config:
        def get_markets(self):
            return []

        def get_exchanges(self):
            return [object()]

    called = []
    monkeypatch.setattr(Configurator, "setup_gateway", lambda self, exchange: called.append(exchange))

    configurator = Configurator(Config(), GatewayConfig(GatewayMode.NONE, None))

    assert called == []
    assert configurator.exchanges == {}
