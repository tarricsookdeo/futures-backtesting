"""
Example demonstrating data loader and trade journal features.

This shows how to:
1. Load TradingView CSV data
2. Run a backtest with trade journal
3. Export journal for analysis
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '..')

from futures_backtesting import (
    BaseStrategy, BacktestEngine, MultiDataFeed,
    TOPSTEP_50K, OrderType,
    DataLoader, load_tradingview,
    TradeJournal, create_trade_journal
)


class SMACrossStrategy(BaseStrategy):
    """Simple SMA crossover strategy with OCO brackets."""
    
    def __init__(self, fast=10, slow=30, tp_ticks=20, sl_ticks=10):
        super().__init__()
        self.fast = fast
        self.slow = slow
        self.tp_ticks = tp_ticks
        self.sl_ticks = sl_ticks
    
    def initialize(self):
        """Calculate SMAs."""
        for symbol in self.data.get_symbols():
            feed = self.get_data(symbol)
            closes = feed.data['close']
            feed.data[f'sma_{self.fast}'] = closes.rolling(self.fast).mean()
            feed.data[f'sma_{self.slow}'] = closes.rolling(self.slow).mean()
    
    def next(self):
        """Trading logic."""
        for symbol in self.data.get_symbols():
            if not self.is_flat(symbol):
                continue
            
            feed = self.get_data(symbol)
            idx = feed._idx
            
            if idx < self.slow:
                continue
            
            fast_sma = feed.data[f'sma_{self.fast}'].iloc[idx]
            slow_sma = feed.data[f'sma_{self.slow}'].iloc[idx]
            prev_fast = feed.data[f'sma_{self.fast}'].iloc[idx - 1]
            prev_slow = feed.data[f'sma_{self.slow}'].iloc[idx - 1]
            
            # Golden cross
            if prev_fast <= prev_slow and fast_sma > slow_sma:
                self.buy_bracket(
                    symbol=symbol,
                    size=1,
                    take_profit_ticks=self.tp_ticks,
                    stop_loss_ticks=self.sl_ticks
                )
            
            # Death cross
            elif prev_fast >= prev_slow and fast_sma < slow_sma:
                self.sell_bracket(
                    symbol=symbol,
                    size=1,
                    take_profit_ticks=self.tp_ticks,
                    stop_loss_ticks=self.sl_ticks
                )


def create_sample_data(filepath: str):
    """Create sample TradingView format CSV."""
    np.random.seed(42)
    n = 500
    
    # Generate trending price data
    trend = np.linspace(0, 100, n)
    noise = np.cumsum(np.random.randn(n) * 0.5)
    closes = 4500 + trend + noise
    
    df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='15min'),
        'open': closes * (1 + np.random.randn(n) * 0.0005),
        'high': closes * (1 + abs(np.random.randn(n)) * 0.001),
        'low': closes * (1 - abs(np.random.randn(n)) * 0.001),
        'close': closes,
        'Volume': np.random.randint(1000, 10000, n)
    })
    
    # Fix OHLC
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    df.to_csv(filepath, index=False)
    print(f"Created sample data: {filepath}")
    return filepath


if __name__ == "__main__":
    print("="*70)
    print("Data Loader & Trade Journal Example")
    print("="*70)
    
    # Create sample data
    data_file = "/tmp/MES_15min_sample.csv"
    create_sample_data(data_file)
    
    # Load data using TradingView loader
    print("\n1. Loading TradingView CSV data...")
    df = load_tradingview(data_file, symbol="MES")
    print(f"   Loaded {len(df)} bars")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Symbol (detected): {df.attrs.get('symbol')}")
    print(f"   Timeframe (detected): {df.attrs.get('timeframe')}")
    
    # Set up data feed
    feed = MultiDataFeed()
    feed.add_data(df, "MES", "15min")
    
    # Create trade journal
    print("\n2. Creating trade journal...")
    journal = create_trade_journal("SMA Crossover Backtest")
    
    # Run backtest with journal
    print("\n3. Running backtest with trade journal...")
    engine = BacktestEngine(
        data=feed,
        strategy_class=SMACrossStrategy,
        prop_firm_config=TOPSTEP_50K,
        commission_per_contract=2.50,
        strategy_params={
            'fast': 10,
            'slow': 30,
            'tp_ticks': 20,
            'sl_ticks': 10
        },
        journal=journal  # Pass journal to engine
    )
    
    results = engine.run()
    
    # Print results
    print("\n" + "="*70)
    print(engine.get_summary())
    
    # Print journal statistics
    print("\n4. Trade Journal Statistics:")
    journal.print_summary()
    
    # Export journal
    print("\n5. Exporting journal...")
    
    # Export to CSV
    csv_path = "/tmp/trade_journal.csv"
    journal.export_csv(csv_path)
    print(f"   CSV exported: {csv_path}")
    
    # Export to JSON
    json_path = "/tmp/trade_journal.json"
    journal.export_json(json_path)
    print(f"   JSON exported: {json_path}")
    
    # Show sample journal entries
    print("\n6. Sample Journal Entries:")
    entries = list(journal.entries.values())[:3]
    for entry in entries:
        print(f"\n   Trade {entry.trade_id}:")
        print(f"     {entry.side} {entry.size} {entry.symbol}")
        print(f"     Entry: ${entry.entry_price:.2f} at {entry.entry_time}")
        print(f"     Exit:  ${entry.exit_price:.2f} at {entry.exit_time}")
        print(f"     P&L:   ${entry.net_pnl:+.2f}")
        print(f"     Duration: {entry.duration_minutes:.0f} minutes")
    
    print("\n" + "="*70)
    print("Example complete!")
    print("\nKey takeaways:")
    print("- DataLoader auto-detects TradingView format")
    print("- TradeJournal captures detailed trade information")
    print("- Export to CSV for Excel analysis")
    print("- Export to JSON for programmatic access")
    print("="*70)
