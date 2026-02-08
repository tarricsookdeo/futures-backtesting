"""
Futures Backtesting Framework

A Python framework for backtesting futures trading strategies,
specifically designed for prop firm evaluation.
"""

__version__ = "0.1.0"

# Core components
from .core.backtest import BacktestEngine, BacktestResult
from .core.strategy import BaseStrategy
from .core.orders import Order, OrderType, OrderSide
from .core.data import DataFeed, MultiDataFeed
from .core.risk import RiskManager
from .core.metrics import calculate_all_metrics, format_metrics
from .core.plotting import (
    plot_equity_curve,
    plot_monthly_returns,
    plot_trade_distribution,
    create_full_report
)

# Contracts
from .contracts.micros import (
    ContractSpec,
    MES, MNQ, MGC, MYM,
    get_contract,
    calculate_pnl,
    CONTRACTS
)

# Prop Firms
from .prop_firms.configs import (
    PropFirmConfig,
    DrawdownType,
    get_prop_firm,
    TOPSTEP_50K,
    TOPSTEP_100K,
    TOPSTEP_150K,
    LUCID_50K,
    LUCID_100K,
    TAKE_PROFIT_50K,
    TAKE_PROFIT_100K
)

__all__ = [
    # Core
    'BacktestEngine',
    'BacktestResult',
    'BaseStrategy',
    'Order',
    'OrderType',
    'OrderSide',
    'DataFeed',
    'MultiDataFeed',
    'RiskManager',
    
    # Metrics & Plotting
    'calculate_all_metrics',
    'format_metrics',
    'plot_equity_curve',
    'plot_monthly_returns',
    'plot_trade_distribution',
    'create_full_report',
    
    # Contracts
    'ContractSpec',
    'MES',
    'MNQ',
    'MGC',
    'MYM',
    'get_contract',
    'calculate_pnl',
    'CONTRACTS',
    
    # Prop Firms
    'PropFirmConfig',
    'DrawdownType',
    'get_prop_firm',
    'TOPSTEP_50K',
    'TOPSTEP_100K',
    'TOPSTEP_150K',
    'LUCID_50K',
    'LUCID_100K',
    'TAKE_PROFIT_50K',
    'TAKE_PROFIT_100K',
]
