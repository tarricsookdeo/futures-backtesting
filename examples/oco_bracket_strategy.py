"""
Example strategy using OCO (One-Cancels-Other) bracket orders.

This demonstrates how to use buy_bracket() and sell_bracket() with
configurable take profit and stop loss in ticks.
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '..')

from futures_backtesting import (
    BaseStrategy, BacktestEngine, MultiDataFeed,
    TOPSTEP_50K, OrderType
)


class OCOBracketStrategy(BaseStrategy):
    """
    Strategy demonstrating OCO bracket orders.
    
    Enters long when price crosses above SMA, with bracket orders:
    - Take Profit: 20 ticks above entry
    - Stop Loss: 10 ticks below entry
    
    The TP and SL are linked as an OCO pair - when one fills,
    the other is automatically cancelled.
    """
    
    def __init__(self, sma_period=20, tp_ticks=20, sl_ticks=10):
        super().__init__()
        self.sma_period = sma_period
        self.tp_ticks = tp_ticks
        self.sl_ticks = sl_ticks
        self._bracket_active = {}  # Track active bracket orders per symbol
        
    def initialize(self):
        """Set up indicators."""
        for symbol in self.data.get_symbols():
            feed = self.get_data(symbol)
            closes = feed.data['close']
            feed.data[f'sma_{self.sma_period}'] = closes.rolling(self.sma_period).mean()
    
    def next(self):
        """Execute strategy logic."""
        for symbol in self.data.get_symbols():
            # Skip if we already have a bracket active for this symbol
            if symbol in self._bracket_active:
                # Check if bracket was filled (position closed)
                if self.is_flat(symbol):
                    del self._bracket_active[symbol]
                continue
            
            feed = self.get_data(symbol)
            current_idx = feed._idx
            
            # Need enough data
            if current_idx < self.sma_period:
                continue
            
            # Get current and previous values
            close = self.get_close(symbol)
            sma = feed.data[f'sma_{self.sma_period}'].iloc[current_idx]
            prev_close = feed.data['close'].iloc[current_idx - 1]
            prev_sma = feed.data[f'sma_{self.sma_period}'].iloc[current_idx - 1]
            
            # Check for SMA crossover (price crosses above SMA)
            if prev_close <= prev_sma and close > sma:
                if self.is_flat(symbol):
                    # Enter bracket order
                    entry_id, tp_id, sl_id = self.buy_bracket(
                        symbol=symbol,
                        size=1,
                        take_profit_ticks=self.tp_ticks,
                        stop_loss_ticks=self.sl_ticks
                    )
                    self._bracket_active[symbol] = {
                        'entry_id': entry_id,
                        'tp_id': tp_id,
                        'sl_id': sl_id,
                        'entry_price': close
                    }
                    print(f"[{self.get_datetime()}] Buy Bracket: Entry@{close:.2f}, "
                          f"TP+{self.tp_ticks}ticks, SL-{self.sl_ticks}ticks")
    
    def notify_order(self, order):
        """Track order fills."""
        if order.is_filled():
            for symbol, bracket in self._bracket_active.items():
                if order.order_id == bracket['entry_id']:
                    print(f"  Entry filled at {order.fill_price:.2f}")
                elif order.order_id == bracket['tp_id']:
                    print(f"  Take Profit filled at {order.fill_price:.2f}")
                elif order.order_id == bracket['sl_id']:
                    print(f"  Stop Loss filled at {order.fill_price:.2f}")


if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    n_bars = 1000
    
    # Generate trending data for better bracket results
    trend = np.linspace(0, 50, n_bars)
    returns = np.random.randn(n_bars) * 0.5
    closes = 4500 + trend + np.cumsum(returns)
    
    data = pd.DataFrame({
        'open': closes * (1 + np.random.randn(n_bars) * 0.0005),
        'high': closes * (1 + abs(np.random.randn(n_bars)) * 0.001),
        'low': closes * (1 - abs(np.random.randn(n_bars)) * 0.001),
        'close': closes,
        'volume': np.random.randint(1000, 10000, n_bars)
    }, index=pd.date_range('2024-01-01', periods=n_bars, freq='5min'))
    
    # Ensure OHLC relationship
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    # Set up backtest
    feed = MultiDataFeed()
    feed.add_data(data, 'MES', '5min')
    
    print("="*60)
    print("OCO Bracket Order Example")
    print("="*60)
    print("Configuration:")
    print("  Contract: MES (Micro E-mini S&P 500)")
    print("  Tick Size: 0.25")
    print("  Tick Value: $1.25")
    print("  Take Profit: 20 ticks ($25.00)")
    print("  Stop Loss: 10 ticks ($12.50)")
    print("="*60)
    
    engine = BacktestEngine(
        data=feed,
        strategy_class=OCOBracketStrategy,
        prop_firm_config=TOPSTEP_50K,
        commission_per_contract=2.50,
        strategy_params={
            'sma_period': 20,
            'tp_ticks': 20,
            'sl_ticks': 10
        }
    )
    
    results = engine.run()
    
    print("\n" + "="*60)
    print(engine.get_summary())
    
    # Show OCO statistics
    print("\nOCO Bracket Statistics:")
    tp_fills = sum(1 for t in results.trades if t['net_pnl'] > 5)  # Approximate TP fills
    sl_fills = sum(1 for t in results.trades if t['net_pnl'] < -5)  # Approximate SL fills
    print(f"  Take Profit hits: ~{tp_fills}")
    print(f"  Stop Loss hits: ~{sl_fills}")
    
    # Plot results
    try:
        from futures_backtesting import plot_equity_curve
        import plotly.offline as pyo
        
        fig = plot_equity_curve(results.equity_curve, results.trades,
                               "OCO Bracket Strategy - MES")
        pyo.plot(fig, filename='oco_bracket_results.html')
        print("\nPlot saved to oco_bracket_results.html")
    except ImportError:
        print("\nInstall plotly to generate interactive plots: pip install plotly")
