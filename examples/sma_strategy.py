"""
Simple Moving Average Crossover Strategy Example
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '..')

from futures_backtesting import (
    BaseStrategy, BacktestEngine, MultiDataFeed,
    TOPSTEP_50K, OrderType
)


class SMAStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    
    Buys when short SMA crosses above long SMA.
    Sells when short SMA crosses below long SMA.
    """
    
    def __init__(self, short_period=20, long_period=50):
        super().__init__()
        self.short_period = short_period
        self.long_period = long_period
        
    def initialize(self):
        """Set up indicators."""
        # Pre-calculate SMAs for all symbols
        for symbol in self.data.get_symbols():
            feed = self.get_data(symbol)
            closes = feed.data['close']
            
            # Add indicators to feed data
            feed.data[f'sma_{self.short_period}'] = closes.rolling(self.short_period).mean()
            feed.data[f'sma_{self.long_period}'] = closes.rolling(self.long_period).mean()
    
    def next(self):
        """Execute strategy logic."""
        for symbol in self.data.get_symbols():
            feed = self.get_data(symbol)
            
            # Get current index
            current_idx = feed._idx
            
            # Need enough data for both SMAs
            if current_idx < self.long_period:
                continue
            
            # Get current and previous SMA values
            current_close = self.get_close(symbol)
            current_short = feed.data[f'sma_{self.short_period}'].iloc[current_idx]
            current_long = feed.data[f'sma_{self.long_period}'].iloc[current_idx]
            prev_short = feed.data[f'sma_{self.short_period}'].iloc[current_idx - 1]
            prev_long = feed.data[f'sma_{self.long_period}'].iloc[current_idx - 1]
            
            # Check for crossover
            position = self.get_position(symbol)
            
            # Golden cross (short above long)
            if prev_short <= prev_long and current_short > current_long:
                if position <= 0:  # Not long
                    if position < 0:
                        self.close(symbol)  # Close short
                    self.buy(symbol, size=1)
            
            # Death cross (short below long)
            elif prev_short >= prev_long and current_short < current_long:
                if position >= 0:  # Not short
                    if position > 0:
                        self.close(symbol)  # Close long
                    self.sell(symbol, size=1)


if __name__ == "__main__":
    # Create sample data (you would use real data here)
    # This generates synthetic OHLCV data
    np.random.seed(42)
    n_bars = 1000
    
    # Generate random walk prices
    returns = np.random.randn(n_bars) * 0.001
    closes = 4500 * np.exp(np.cumsum(returns))
    
    # Generate OHLC
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
    
    # Set up data feed
    feed = MultiDataFeed()
    feed.add_data(data, 'MES', '5min')
    
    # Create and run backtest
    engine = BacktestEngine(
        data=feed,
        strategy_class=SMAStrategy,
        prop_firm_config=TOPSTEP_50K,
        commission_per_contract=2.50,
        strategy_params={'short_period': 20, 'long_period': 50}
    )
    
    results = engine.run()
    
    # Print results
    print(engine.get_summary())
    
    # Plot results (optional - requires plotly)
    try:
        from futures_backtesting import plot_equity_curve
        import plotly.offline as pyo
        
        fig = plot_equity_curve(results.equity_curve, results.trades, 
                               "SMA Crossover Strategy")
        pyo.plot(fig, filename='sma_strategy_results.html')
        print("\nPlot saved to sma_strategy_results.html")
    except ImportError:
        print("\nInstall plotly to generate interactive plots: pip install plotly")
