"""
Main backtesting engine.
"""
from typing import Optional, Dict, List, Type
from datetime import datetime
import pandas as pd
import numpy as np

from .data import MultiDataFeed
from .strategy import BaseStrategy
from .orders import OrderManager, Position, Order
from .risk import RiskManager
from ..prop_firms.configs import PropFirmConfig
from ..contracts.micros import calculate_pnl, get_contract
from ..utils.journal import TradeJournal, TradeJournalEntry


class BacktestResult:
    """Container for backtest results."""
    
    def __init__(self):
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.orders: List[Order] = []
        self.daily_stats: List[Dict] = []
        self.metrics: Dict = {}
        
    def add_trade(self, timestamp: datetime, symbol: str, side: str, 
                  size: int, entry_price: float, exit_price: float,
                  pnl: float, commission: float):
        """Add a completed trade."""
        self.trades.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'size': size,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'commission': commission,
            'net_pnl': pnl - commission
        })
    
    def add_equity_point(self, timestamp: datetime, equity: float, 
                         cash: float, positions_value: float):
        """Add equity curve point."""
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': equity,
            'cash': cash,
            'positions_value': positions_value
        })
    
    def calculate_metrics(self, initial_equity: float):
        """Calculate performance metrics."""
        if not self.trades:
            self.metrics = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_return': 0.0,
                'total_pnl': 0.0,
                'total_commission': 0.0,
                'net_profit': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'avg_trade': 0.0,
            }
            return
        
        # Basic trade metrics
        total_trades = len(self.trades)
        net_pnls = [t['net_pnl'] for t in self.trades]
        winning_trades = [p for p in net_pnls if p > 0]
        losing_trades = [p for p in net_pnls if p < 0]
        
        # P&L metrics
        total_pnl = sum(t['pnl'] for t in self.trades)
        total_commission = sum(t['commission'] for t in self.trades)
        net_profit = total_pnl - total_commission
        
        # Returns
        final_equity = self.equity_curve[-1]['equity'] if self.equity_curve else initial_equity
        total_return = (final_equity - initial_equity) / initial_equity
        
        # Win rate
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # Profit factor
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe ratio (daily returns)
        if len(self.equity_curve) > 1:
            equity_df = pd.DataFrame(self.equity_curve)
            equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
            equity_df.set_index('timestamp', inplace=True)
            daily_returns = equity_df['equity'].resample('D').last().pct_change().dropna()
            
            if len(daily_returns) > 1 and daily_returns.std() > 0:
                sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        # Max drawdown
        if self.equity_curve:
            equity_values = [e['equity'] for e in self.equity_curve]
            peak = equity_values[0]
            max_dd = 0
            max_dd_pct = 0
            for eq in equity_values:
                if eq > peak:
                    peak = eq
                dd = peak - eq
                dd_pct = dd / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
                max_dd_pct = max(max_dd_pct, dd_pct)
        else:
            max_dd = 0
            max_dd_pct = 0
        
        self.metrics = {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_return': total_return,
            'total_pnl': total_pnl,
            'total_commission': total_commission,
            'net_profit': net_profit,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'avg_trade': net_profit / total_trades if total_trades > 0 else 0,
        }


class BacktestEngine:
    """
    Main backtesting engine.
    
    Usage:
        engine = BacktestEngine(data, strategy_class, prop_firm_config)
        results = engine.run()
    """
    
    def __init__(self,
                 data: MultiDataFeed,
                 strategy_class: Type[BaseStrategy],
                 prop_firm_config: PropFirmConfig,
                 commission_per_contract: float = 2.50,
                 strategy_params: Optional[Dict] = None,
                 journal: Optional[TradeJournal] = None):
        """
        Initialize backtest engine.

        Args:
            data: MultiDataFeed with OHLCV data
            strategy_class: Strategy class (subclass of BaseStrategy)
            prop_firm_config: Prop firm configuration
            commission_per_contract: Commission per contract per side
            strategy_params: Optional parameters to pass to strategy
            journal: Optional TradeJournal to populate with trade details
        """
        self.data = data
        self.strategy_class = strategy_class
        self.prop_firm_config = prop_firm_config
        self.commission_per_contract = commission_per_contract
        self.strategy_params = strategy_params or {}
        self.journal = journal

        # Initialize components
        self.broker = OrderManager()
        self.risk_manager = RiskManager(prop_firm_config)
        self.strategy: Optional[BaseStrategy] = None

        # State
        self.cash = prop_firm_config.initial_balance
        self.equity = prop_firm_config.initial_balance
        self.current_time: Optional[datetime] = None

        # Results
        self.results = BacktestResult()
        self._trade_log: Dict[str, Dict] = {}  # Track open trades
        self._journal_entries: Dict[str, TradeJournalEntry] = {}  # Track journal entries
        
    def run(self) -> BacktestResult:
        """Run the backtest."""
        # Initialize strategy
        self.strategy = self.strategy_class(**self.strategy_params)
        self.strategy.broker = self.broker
        self.strategy.data = self.data
        self.strategy.initialize()
        
        # Run through data
        for timestamp, bar_data in self.data:
            self.current_time = timestamp
            
            # Update risk manager
            risk_status = self.risk_manager.update(timestamp, self.equity)
            
            if risk_status['close_positions']:
                # Close all positions due to risk violation
                close_orders = self.broker.close_all_positions(timestamp, {s: b['close'] for s, b in bar_data.items()})
                for order in close_orders:
                    order.status = Order.OrderStatus.PENDING
                    self.broker.submit_order(order)
            
            if not risk_status['can_trade']:
                # Skip to next bar if we can't trade
                continue
            
            # Process any pending orders
            fills = self.broker.process_pending(timestamp, bar_data)
            
            # Update positions and record fills
            for order, fill_price in fills:
                self._process_fill(order, fill_price, timestamp)
            
            # Update strategy with new bar
            self.strategy.next()
            
            # Calculate current equity
            self._update_equity(bar_data, timestamp)
        
        # Calculate final metrics
        self.results.calculate_metrics(self.prop_firm_config.initial_balance)
        
        return self.results
    
    def _process_fill(self, order: Order, fill_price: float, timestamp: datetime):
        """Process an order fill."""
        symbol = order.symbol
        size = order.size if order.is_buy() else -order.size

        # Get position before update
        position = self.broker.get_position(symbol)
        prev_size = position.size

        # Update position
        position.update(fill_price, size, timestamp)

        # Calculate commission
        commission = abs(size) * self.commission_per_contract
        self.cash -= commission

        # Check if this closed a trade
        if prev_size != 0 and position.size == 0:
            # Trade completed
            entry_info = self._trade_log.get(symbol)
            if entry_info:
                contract = get_contract(symbol)
                pnl = calculate_pnl(symbol, entry_info['price'], fill_price, entry_info['size'])
                side = 'LONG' if entry_info['size'] > 0 else 'SHORT'

                self.results.add_trade(
                    timestamp=timestamp,
                    symbol=symbol,
                    side=side,
                    size=abs(entry_info['size']),
                    entry_price=entry_info['price'],
                    exit_price=fill_price,
                    pnl=pnl,
                    commission=commission
                )

                # Create journal entry if journal is enabled
                if self.journal:
                    entry = TradeJournalEntry(
                        entry_time=entry_info['timestamp'],
                        exit_time=timestamp,
                        symbol=symbol,
                        side=side,
                        size=abs(entry_info['size']),
                        entry_price=entry_info['price'],
                        exit_price=fill_price,
                        gross_pnl=pnl,
                        commission=commission,
                        net_pnl=pnl - commission
                    )
                    self.journal.add_entry(entry)

                self._trade_log.pop(symbol, None)

        elif prev_size == 0 and position.size != 0:
            # New trade opened
            self._trade_log[symbol] = {
                'price': fill_price,
                'size': position.size,
                'timestamp': timestamp
            }

        # Notify strategy
        self.strategy.notify_order(order)

        # Notify trade completion (only if we just closed a position)
        if prev_size != 0 and position.size == 0:
            # Recalculate for notification (entry_info was popped)
            entry_info = None
            for trade in position.trades:
                if trade['position_after'] != 0:
                    entry_info = trade

            if entry_info:
                contract = get_contract(symbol)
                pnl = calculate_pnl(symbol, entry_info['price'], fill_price, entry_info['size'])
                self.strategy.notify_trade(symbol, entry_info['size'], entry_info['price'], fill_price, pnl)
    
    def _update_equity(self, bar_data: Dict, timestamp: datetime):
        """Update equity based on positions and current prices."""
        positions_value = 0
        
        for symbol, position in self.broker.positions.items():
            if position.is_flat():
                continue
            
            if symbol in bar_data:
                bar = bar_data[symbol]
                contract = get_contract(symbol)
                unrealized = position.unrealized_pnl(bar['close'], contract.tick_value, contract.tick_size)
                positions_value += unrealized
        
        self.equity = self.cash + positions_value
        self.results.add_equity_point(timestamp, self.equity, self.cash, positions_value)
    
    def get_summary(self) -> str:
        """Get summary string of backtest results."""
        if not self.results.metrics:
            return "No results yet. Run backtest first."
        
        m = self.results.metrics
        return f"""
Backtest Results for {self.prop_firm_config.name}
{'='*50}
Total Trades: {m['total_trades']}
Win Rate: {m['win_rate']:.1%}
Profit Factor: {m['profit_factor']:.2f}
Sharpe Ratio: {m['sharpe_ratio']:.2f}

P&L:
  Gross P&L: ${m['total_pnl']:,.2f}
  Commissions: ${m['total_commission']:,.2f}
  Net Profit: ${m['net_profit']:,.2f}
  Total Return: {m['total_return']:.1%}

Risk:
  Max Drawdown: ${m['max_drawdown']:,.2f} ({m['max_drawdown_pct']:.1%})
  Avg Trade: ${m['avg_trade']:,.2f}
"""
