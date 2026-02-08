"""
Prop firm configurations for various futures trading firms.
"""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class DrawdownType(Enum):
    """Types of drawdown tracking."""
    EOD_TRAILING = "eod_trailing"  # End-of-day trailing drawdown
    INTRADAY_TRAILING = "intraday_trailing"  # Intraday trailing drawdown
    STATIC = "static"  # Static max loss


@dataclass(frozen=True)
class PropFirmConfig:
    """Prop firm configuration."""
    name: str
    
    # Account rules
    initial_balance: float
    max_daily_loss: float  # Maximum daily loss allowed
    max_loss: float  # Maximum total loss (static trailing)
    
    # Drawdown settings
    drawdown_type: DrawdownType
    drawdown_start_value: float  # What value drawdown trails from (balance or high water mark)
    
    # Time rules
    position_close_time: str  # Time when all positions must be closed (ET)
    trading_start_time: Optional[str] = None  # When trading can start
    trading_end_time: Optional[str] = None  # When trading must end
    
    # Other rules
    allow_overnight: bool = False
    max_contracts: Optional[int] = None
    profit_target: Optional[float] = None  # Profit target for evaluation
    min_trading_days: int = 0
    
    def __repr__(self):
        return f"{self.name} Config"


# Topstep configuration
TOPSTEP_50K = PropFirmConfig(
    name="Topstep 50K",
    initial_balance=50000.0,
    max_daily_loss=1000.0,
    max_loss=2000.0,
    drawdown_type=DrawdownType.EOD_TRAILING,
    drawdown_start_value=50000.0,
    position_close_time="16:00",  # 4:00 PM ET
    trading_start_time="18:00",  # Previous day for globex
    trading_end_time="16:00",
    allow_overnight=False,
    max_contracts=5,
    profit_target=3000.0,
    min_trading_days=4
)

TOPSTEP_100K = PropFirmConfig(
    name="Topstep 100K",
    initial_balance=100000.0,
    max_daily_loss=2000.0,
    max_loss=3000.0,
    drawdown_type=DrawdownType.EOD_TRAILING,
    drawdown_start_value=100000.0,
    position_close_time="16:00",
    trading_start_time="18:00",
    trading_end_time="16:00",
    allow_overnight=False,
    max_contracts=10,
    profit_target=6000.0,
    min_trading_days=4
)

TOPSTEP_150K = PropFirmConfig(
    name="Topstep 150K",
    initial_balance=150000.0,
    max_daily_loss=3000.0,
    max_loss=4500.0,
    drawdown_type=DrawdownType.EOD_TRAILING,
    drawdown_start_value=150000.0,
    position_close_time="16:00",
    trading_start_time="18:00",
    trading_end_time="16:00",
    allow_overnight=False,
    max_contracts=15,
    profit_target=9000.0,
    min_trading_days=4
)

# Lucid Trading configuration
LUCID_50K = PropFirmConfig(
    name="Lucid 50K",
    initial_balance=50000.0,
    max_daily_loss=1000.0,
    max_loss=2500.0,
    drawdown_type=DrawdownType.INTRADAY_TRAILING,
    drawdown_start_value=50000.0,
    position_close_time="17:00",  # 5:00 PM ET
    allow_overnight=False,
    max_contracts=5,
    profit_target=2500.0,
    min_trading_days=3
)

LUCID_100K = PropFirmConfig(
    name="Lucid 100K",
    initial_balance=100000.0,
    max_daily_loss=2000.0,
    max_loss=3500.0,
    drawdown_type=DrawdownType.INTRADAY_TRAILING,
    drawdown_start_value=100000.0,
    position_close_time="17:00",
    allow_overnight=False,
    max_contracts=10,
    profit_target=5000.0,
    min_trading_days=3
)

# Take Profit Trader configuration
TAKE_PROFIT_50K = PropFirmConfig(
    name="Take Profit Trader 50K",
    initial_balance=50000.0,
    max_daily_loss=1250.0,
    max_loss=2500.0,
    drawdown_type=DrawdownType.INTRADAY_TRAILING,
    drawdown_start_value=50000.0,
    position_close_time="17:00",  # 5:00 PM ET
    allow_overnight=False,
    max_contracts=5,
    profit_target=3000.0,
    min_trading_days=3
)

TAKE_PROFIT_100K = PropFirmConfig(
    name="Take Profit Trader 100K",
    initial_balance=100000.0,
    max_daily_loss=2500.0,
    max_loss=3500.0,
    drawdown_type=DrawdownType.INTRADAY_TRAILING,
    drawdown_start_value=100000.0,
    position_close_time="17:00",
    allow_overnight=False,
    max_contracts=10,
    profit_target=6000.0,
    min_trading_days=3
)


# Registry of all prop firm configs
PROP_FIRMS = {
    "topstep_50k": TOPSTEP_50K,
    "topstep_100k": TOPSTEP_100K,
    "topstep_150k": TOPSTEP_150K,
    "lucid_50k": LUCID_50K,
    "lucid_100k": LUCID_100K,
    "take_profit_50k": TAKE_PROFIT_50K,
    "take_profit_100k": TAKE_PROFIT_100K,
}


def get_prop_firm(name: str) -> PropFirmConfig:
    """Get prop firm configuration by name."""
    name = name.lower().replace(" ", "_")
    if name not in PROP_FIRMS:
        raise ValueError(f"Unknown prop firm: {name}. Available: {list(PROP_FIRMS.keys())}")
    return PROP_FIRMS[name]
