"""An environment's markets and venues, wired into a runtime.

This is where a configuration becomes objects that can connect. It asks `qate`'s
registry for whatever adapter is installed, so it names no venue itself -- and it
reaches `sys_env` for credentials, which is why it lives here rather than in the
public library: the one package that knows where the keys are is the one that
should be allowed to hand them to a gateway.

Without an adapter installed there is nothing for it to build, and with
`GatewayName.SIMULATOR` it builds nothing that could reach one.
"""

from dataclasses import dataclass
from logging import getLogger

from qate.core.conn import PrivateConnection, PublicConnection
from qate.core.feed import ExchangeFeed, MarketDataFeed
from qate.core.gateway import ExchangeGateway
from qate.core.model import ExchangeName
from qate.exchange import factory, registry
from qate.trading.config import StrategyConfig
from qate.trading.gateways import SimulatorGateway
from qate.trading.runtime import Runtime

from . import sys_env
from .trading_env import TradingProfile

LOG = getLogger(__name__)


class GatewayName:
    PROD = "PROD"
    SIMULATOR = "SIMULATOR"


@dataclass
class ExchangeComponents:
    public_conn: PublicConnection = None
    private_conn: PrivateConnection = None
    market_feed: MarketDataFeed = None
    exchange_feed: ExchangeFeed = None
    gateway: ExchangeGateway = None


class Configurator:
    """Wires an environment's markets and venues into a runtime.

    `gateway_name` is the runner's decision, not the environment's: a live runner
    passes PROD, a paper or replay runner leaves it as SIMULATOR.
    """

    def __init__(
        self,
        config: StrategyConfig,
        profile: TradingProfile,
        gateway_name: str = GatewayName.SIMULATOR,
    ):
        self.gateway_name = gateway_name
        self.exchanges: dict[ExchangeName, ExchangeComponents] = {}
        for market, event_type_list in config.get_markets():
            self.setup_market_data(market, event_type_list)
        for exchange_name in config.get_exchanges():
            self.setup_gateway(exchange_name, profile)

    def setup_market_data(self, market, event_type_list):
        exchange_name = market.exchange_name
        if exchange_name not in self.exchanges:
            public_conn = factory.create_public_connection(exchange_name)
            components = ExchangeComponents()
            components.public_conn = public_conn
            components.market_feed = public_conn
            self.exchanges[exchange_name] = components

        components = self.exchanges.get(exchange_name)
        for event_type in event_type_list:
            components.market_feed.register_symbol_event(market.symbol, event_type)

    def setup_gateway(self, exchange_name: ExchangeName, profile: TradingProfile):
        components = self.exchanges.get(exchange_name)

        if self.gateway_name != GatewayName.PROD:
            gateway = SimulatorGateway(exchange_name)
            gateway.subscribe_market_data_feed(components.market_feed)
            components.gateway = gateway
            return

        (api_key, secret) = sys_env.get_api_keys(exchange_name.name, profile.trading_config_key)
        gateway = factory.create_exchange_gateway(exchange_name, api_key, secret)

        # Whether a venue has an account feed is the adapter's own answer.
        # Enumerating the venues that do here meant this file had to be edited
        # every time one was added, and it is not this file's knowledge to hold.
        if registry.get(exchange_name).create_private_connection:
            private_conn = factory.create_private_connection(gateway.api)
            components.private_conn = private_conn
            components.exchange_feed = private_conn

        if components.exchange_feed:
            gateway.subscribe_exchange_feed(components.exchange_feed)
        components.gateway = gateway

    def configure(self, runtime: Runtime):
        for components in self.exchanges.values():
            if components.public_conn:
                runtime.add_conn(components.public_conn)
            if components.private_conn:
                runtime.add_conn(components.private_conn)
            if components.gateway:
                runtime.add_gateway(components.gateway)
