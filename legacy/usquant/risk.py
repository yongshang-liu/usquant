import math
from dataclasses import dataclass

@dataclass
class RiskLimits:
    max_position_fraction: float = 0.20
    max_order_notional: float = 500.0
    max_drawdown: float = 0.08
    max_daily_loss: float = 0.03
    max_volume_fraction: float = 0.01
    kill_switch: bool = False

    def __post_init__(self):
        for key in ('max_position_fraction','max_drawdown','max_daily_loss','max_volume_fraction'):
            val = getattr(self,key)
            if not math.isfinite(val) or not 0 < val <= 1: raise ValueError('invalid '+key)
        if not math.isfinite(self.max_order_notional) or self.max_order_notional <= 0:
            raise ValueError('invalid order limit')
        if type(self.kill_switch) is not bool: raise ValueError('kill_switch must be boolean')

    def halted(self, equity, peak, previous_close):
        return self.kill_switch or equity <= 0 or equity <= peak*(1-self.max_drawdown) or equity <= previous_close*(1-self.max_daily_loss)
