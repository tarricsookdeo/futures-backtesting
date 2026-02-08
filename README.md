# Futures Backtesting Framework

A Python framework for backtesting futures trading strategies, specifically designed for prop firm evaluation. Modeled after the popular [backtrader](https://www.backtrader.com/) library with built-in support for micro futures contracts and prop firm risk rules.

## Features

- **Micro Futures Support**: Pre-configured specs for MNQ, MES, MGC, MYM with tick values and margins
- **Prop Firm Integration**: Built-in rules for Topstep, Lucid, Take Profit Trader
  - Daily loss limits
  - EOD & intraday trailing drawdowns
  - Configurable close times (Topstep: 4pm ET, Others: 5pm ET)
  - Position sizing limits
- **OCO Bracket Orders**: Built-in support for One-Cancels-Other orders
  - Configurable TP/SL in ticks (perfect for prop firm risk management)
  - Automatic cancellation of linked orders
  - Buy and sell bracket support
- **Multi-Timeframe**: Backtest across multiple timeframes (1min to daily)
- **Multi-Instrument**: Trade multiple contracts simultaneously
- **Order Types**: Market, Limit, Stop, Stop-Limit, OCO Brackets
- **Risk Management**: Real-time prop firm rule enforcement
- **Performance Metrics**: Sharpe, Sortino, Profit Factor, Max Drawdown, Calmar, Expectancy
- **Interactive Plotting**: Plotly-based equity curves and trade analysis

## Installation

```bash
git clone https://github.com/tarricsookdeo/futures-backtesting.git
cd futures-backtesting
pip install -r requirements.txt
```

## Quick Start

```python
import pandas as pd
from futures_backtesting import (
    BaseStrategy, BacktestEngine, MultiDataFeed,
    TOPSTEP_50K, OrderType
)

# Create your strategy
class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        
    def initialize(self):
        # Set up indicators here
        pass
    
    def next(self):
        # Trading logic here - called for each bar
        if self.is_flat('MES'):
            self.buy('MES', size=1)
        elif self.get_position('MES') > 0:
            self.close('MES')

# Load your data (OHLCV DataFrame with DatetimeIndex)
data = pd.read_csv('MES_data.csv', index_col='timestamp', parse_dates=True)

# Set up backtest
feed = MultiDataFeed()
feed.add_data(data, 'MES', '5min')

engine = BacktestEngine(
    data=feed,
    strategy_class=MyStrategy,
    prop_firm_config=TOPSTEP_50K,  # Use Topstep 50K rules
    commission_per_contract=2.50
)

# Run backtest
results = engine.run()

# View results
print(engine.get_summary())

# Plot results
from futures_backtesting import plot_equity_curve
fig = plot_equity_curve(results.equity_curve, results.trades)
fig.show()
```

## Data Format

Data should be a pandas DataFrame with a DatetimeIndex and columns:
- `open`: Opening price
- `high`: High price
- `low`: Low price
- `close`: Closing price
- `volume`: Volume

```python
# Example data structure
data = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
}, index=pd.DatetimeIndex([...]))
```

## Strategy Class

Inherit from `BaseStrategy` and override key methods:

```python
class MyStrategy(BaseStrategy):
    def __init__(self, param1=10, param2=20):
        super().__init__()
        self.param1 = param1
        self.param2 = param2
    
    def initialize(self):
        """Called once at start of backtest"""
        # Set up indicators
        pass
    
    def next(self):
        """Called for each bar"""
        # Access data
        close = self.get_close('MES')
        position = self.get_position('MES')
        
        # Place orders
        self.buy('MES', size=1)
        self.sell('MES', size=1)
        self.close('MES')  # Close position
    
    def notify_order(self, order):
        """Called when order status changes"""
        print(f"Order {order.order_id} {order.status}")
    
    def notify_trade(self, symbol, size, entry, exit, pnl):
        """Called when trade completes"""
        print(f"Trade P&L: ${pnl:.2f}")
```

## Prop Firm Configurations

Pre-configured prop firm rules:

```python
from futures_backtesting import (
    TOPSTEP_50K, TOPSTEP_100K, TOPSTEP_150K,
    LUCID_50K, LUCID_100K,
    TAKE_PROFIT_50K, TAKE_PROFIT_100K
)

# Or create custom config
from futures_backtesting import PropFirmConfig, DrawdownType

my_config = PropFirmConfig(
    name="Custom Firm",
    initial_balance=50000,
    max_daily_loss=1000,
    max_loss=2500,
    drawdown_type=DrawdownType.EOD_TRAILING,
    position_close_time="16:00",
    max_contracts=5
)
```

## Contract Specifications

Built-in micro futures specs:

| Symbol | Name | Tick Size | Tick Value | Point Value |
|--------|------|-----------|------------|-------------|
| MES | Micro E-mini S&P 500 | 0.25 | $1.25 | $5.00 |
| MNQ | Micro E-mini Nasdaq-100 | 0.25 | $0.50 | $2.00 |
| MGC | Micro Gold | 0.10 | $1.00 | $10.00 |
| MYM | Micro E-mini Dow | 1.00 | $0.50 | $0.50 |

## OCO Bracket Orders (One-Cancels-Other)

Perfect for prop firm trading with predefined risk/reward. When you enter a position, automatically attach take profit and stop loss orders that are linked together:

```python
# Long bracket - TP 20 ticks above, SL 10 ticks below
entry_id, tp_id, sl_id = self.buy_bracket(
    symbol='MES',
    size=1,
    take_profit_ticks=20,   # 20 ticks = $25 profit for MES
    stop_loss_ticks=10      # 10 ticks = $12.50 risk for MES
)

# Short bracket - TP 20 ticks below, SL 10 ticks above
entry_id, tp_id, sl_id = self.sell_bracket(
    symbol='MNQ',
    size=1,
    take_profit_ticks=20,   # 20 ticks = $10 profit for MNQ
    stop_loss_ticks=10      # 10 ticks = $5 risk for MNQ
)

# With limit entry (entry at specific price)
entry_id, tp_id, sl_id = self.buy_bracket(
    symbol='MES',
    size=1,
    take_profit_ticks=20,
    stop_loss_ticks=10,
    price=4500.00,          # Limit entry at $4500
    exectype=OrderType.LIMIT
)
```

**How it works:**
1. Entry order is submitted
2. TP and SL orders are stored (not active yet)
3. When entry fills → TP and SL become active as an OCO pair
4. When TP or SL fills → the other is automatically cancelled

**Tick Values Reference:**
| Symbol | Tick Size | Tick Value | 20 Ticks | 10 Ticks |
|--------|-----------|------------|----------|----------|
| MES | $0.25 | $1.25 | $25.00 | $12.50 |
| MNQ | $0.25 | $0.50 | $10.00 | $5.00 |
| MGC | $0.10 | $1.00 | $20.00 | $10.00 |
| MYM | $1.00 | $0.50 | $10.00 | $5.00 |

## Order Types

```python
# Market order - fills immediately at market price
self.buy('MES', size=1)
self.sell('MES', size=1)

# Limit order - fills at specified price or better
self.buy('MES', size=1, price=4500, exectype=OrderType.LIMIT)

# Stop order - becomes market order when stop price hit
self.buy('MES', size=1, stop_price=4550, exectype=OrderType.STOP)

# Stop-Limit order - becomes limit order when stop price hit
self.buy('MES', size=1, price=4500, stop_price=4550, exectype=OrderType.STOP_LIMIT)

# Close position
self.close('MES')  # Market order to close position

# Cancel orders
self.cancel(order_id)
self.cancel_all('MES')  # Cancel all orders for symbol
```

## Performance Metrics

The framework calculates:
- Total Return
- Net Profit
- Win Rate
- Profit Factor
- Sharpe Ratio
- Sortino Ratio
- Max Drawdown ($ and %)
- Calmar Ratio
- Expectancy
- Risk of Ruin
- Consecutive Win/Loss Streaks
- Monthly Performance Stats

## Plotting

```python
from futures_backtesting import (
    plot_equity_curve,
    plot_monthly_returns,
    plot_trade_distribution
)

# Equity curve with drawdown
fig = plot_equity_curve(results.equity_curve, results.trades)
fig.show()

# Monthly returns heatmap
fig = plot_monthly_returns(results.equity_curve)
fig.show()

# Trade analysis
fig = plot_trade_distribution(results.trades)
fig.show()
```

## Examples

See the `examples/` directory for complete strategies:

- `sma_strategy.py` - Simple moving average crossover strategy
- `oco_bracket_strategy.py` - Demonstrates OCO bracket orders with configurable TP/SL

Run an example:
```bash
cd examples
python oco_bracket_strategy.py
```

## Project Structure

```
futures-backtesting/
├── futures_backtesting/
│   ├── __init__.py
│   ├── core/
│   │   ├── backtest.py      # Main backtest engine
│   │   ├── data.py          # Data feed handling
│   │   ├── orders.py        # Order/position management
│   │   ├── risk.py          # Risk management
│   │   ├── strategy.py      # Base strategy class
│   │   ├── metrics.py       # Performance metrics
│   │   └── plotting.py      # Visualization
│   ├── contracts/
│   │   └── micros.py        # Micro futures specs
│   └── prop_firms/
│       └── configs.py       # Prop firm configurations
├── examples/
│   └── sma_strategy.py
├── tests/
├── requirements.txt
├── setup.py
└── README.md
```

## Roadmap

- [x] OCO bracket order support
- [x] Prop firm risk management
- [ ] Walk-forward optimization
- [ ] More prop firm configs (Apex, The5ers, etc.)
- [ ] CSV/parquet data loaders
- [ ] Monte Carlo simulation
- [ ] Parameter optimization (grid search, genetic algorithms)
- [ ] Jupyter notebook examples
- [ ] Live trading integration (Interactive Brokers, Tradovate)
- [ ] Multi-threading for faster backtests
- [ ] Custom indicator library
- [ ] Trade journaling and analytics

## License

MIT License - see LICENSE file

## Disclaimer

This software is for educational and research purposes only. Past performance does not guarantee future results. Always test strategies thoroughly before trading with real money.
