"""First exercise: one security, one simulated position, observable order events."""
from AlgorithmImports import *


class FirstBacktest(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2013, 10, 7)
        self.set_end_date(2013, 10, 11)
        self.set_cash(2500)
        self.symbol = self.add_equity('SPY', Resolution.MINUTE).symbol
        self.set_brokerage_model(BrokerageName.QUANT_CONNECT_BROKERAGE, AccountType.CASH)
        self._submitted = False

    def on_data(self, data):
        if self._submitted or not data.bars.contains_key(self.symbol):
            return
        self._submitted = True
        self.debug(f'SIGNAL {self.time}: first available bar; target 20% SPY')
        self.set_holdings(self.symbol, 0.20)

    def on_order_event(self, order_event):
        self.debug(f'ORDER {self.time}: {order_event}')

    def on_end_of_algorithm(self):
        self.debug(f'END portfolio value: {self.portfolio.total_portfolio_value}')
