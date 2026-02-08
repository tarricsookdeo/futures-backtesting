"""
Performance metrics calculation.
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from scipy import stats


def calculate_all_metrics(trades: List[Dict], equity_curve: List[Dict], 
                          initial_equity: float) -> Dict:
    """
    Calculate comprehensive performance metrics.
    
    Args:
        trades: List of trade dictionaries
        equity_curve: List of equity curve points
        initial_equity: Starting equity
        
    Returns:
        Dictionary of metrics
    """
    if not trades or not equity_curve:
        return _empty_metrics()
    
    # Convert to DataFrames
    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_curve)
    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
    equity_df.set_index('timestamp', inplace=True)
    
    metrics = {}
    
    # Trade metrics
    metrics['total_trades'] = len(trades_df)
    metrics['winning_trades'] = len(trades_df[trades_df['net_pnl'] > 0])
    metrics['losing_trades'] = len(trades_df[trades_df['net_pnl'] < 0])
    metrics['win_rate'] = metrics['winning_trades'] / metrics['total_trades'] if metrics['total_trades'] > 0 else 0
    
    # P&L metrics
    metrics['total_pnl'] = trades_df['pnl'].sum()
    metrics['total_commission'] = trades_df['commission'].sum()
    metrics['net_profit'] = trades_df['net_pnl'].sum()
    
    winning_trades = trades_df[trades_df['net_pnl'] > 0]['net_pnl']
    losing_trades = trades_df[trades_df['net_pnl'] < 0]['net_pnl']
    
    metrics['gross_profit'] = winning_trades.sum() if len(winning_trades) > 0 else 0
    metrics['gross_loss'] = losing_trades.sum() if len(losing_trades) > 0 else 0
    
    # Profit factor
    metrics['profit_factor'] = (abs(metrics['gross_profit']) / abs(metrics['gross_loss']) 
                               if metrics['gross_loss'] != 0 else float('inf'))
    
    # Average metrics
    metrics['avg_trade'] = metrics['net_profit'] / metrics['total_trades'] if metrics['total_trades'] > 0 else 0
    metrics['avg_win'] = winning_trades.mean() if len(winning_trades) > 0 else 0
    metrics['avg_loss'] = losing_trades.mean() if len(losing_trades) > 0 else 0
    
    # Expectancy
    metrics['expectancy'] = (metrics['win_rate'] * metrics['avg_win'] + 
                            (1 - metrics['win_rate']) * metrics['avg_loss'])
    
    # Return metrics
    final_equity = equity_df['equity'].iloc[-1]
    metrics['total_return'] = (final_equity - initial_equity) / initial_equity
    metrics['total_return_pct'] = metrics['total_return'] * 100
    
    # Calculate returns for Sharpe/Sortino
    daily_equity = equity_df['equity'].resample('D').last().dropna()
    daily_returns = daily_equity.pct_change().dropna()
    
    # Sharpe ratio (annualized, assuming risk-free rate = 0)
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        metrics['sharpe_ratio'] = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        metrics['sharpe_ratio'] = 0
    
    # Sortino ratio (downside deviation)
    downside_returns = daily_returns[daily_returns < 0]
    if len(downside_returns) > 0 and downside_returns.std() > 0:
        metrics['sortino_ratio'] = (daily_returns.mean() / downside_returns.std()) * np.sqrt(252)
    else:
        metrics['sortino_ratio'] = 0
    
    # Drawdown metrics
    equity_values = equity_df['equity'].values
    peak = np.maximum.accumulate(equity_values)
    drawdown = (peak - equity_values) / peak
    
    metrics['max_drawdown'] = np.max(drawdown)
    metrics['max_drawdown_pct'] = metrics['max_drawdown'] * 100
    metrics['max_drawdown_dollar'] = np.max(peak - equity_values)
    
    # Calmar ratio
    if metrics['max_drawdown'] > 0:
        metrics['calmar_ratio'] = metrics['total_return'] / metrics['max_drawdown']
    else:
        metrics['calmar_ratio'] = 0
    
    # Consecutive wins/losses
    trades_df['win'] = trades_df['net_pnl'] > 0
    trades_df['loss'] = trades_df['net_pnl'] < 0
    
    # Count consecutive wins
    wins = trades_df['win'].astype(int)
    win_groups = (wins != wins.shift()).cumsum()
    win_streaks = wins.groupby(win_groups).sum()
    metrics['max_consecutive_wins'] = win_streaks.max() if len(win_streaks) > 0 else 0
    
    # Count consecutive losses
    losses = trades_df['loss'].astype(int)
    loss_groups = (losses != losses.shift()).cumsum()
    loss_streaks = losses.groupby(loss_groups).sum()
    metrics['max_consecutive_losses'] = loss_streaks.max() if len(loss_streaks) > 0 else 0
    
    # Risk of ruin (simplified)
    win_rate = metrics['win_rate']
    avg_win = metrics['avg_win']
    avg_loss = abs(metrics['avg_loss'])
    
    if avg_loss > 0 and win_rate < 1:
        k = avg_win / avg_loss
        risk_of_ruin = ((1 - win_rate) / win_rate) ** k if win_rate > 0.5 else 1.0
        metrics['risk_of_ruin'] = min(risk_of_ruin, 1.0)
    else:
        metrics['risk_of_ruin'] = 1.0
    
    # Monthly returns
    monthly_returns = equity_df['equity'].resample('ME').last().pct_change().dropna()
    metrics['best_month'] = monthly_returns.max() if len(monthly_returns) > 0 else 0
    metrics['worst_month'] = monthly_returns.min() if len(monthly_returns) > 0 else 0
    metrics['monthly_std'] = monthly_returns.std() if len(monthly_returns) > 0 else 0
    
    return metrics


def _empty_metrics() -> Dict:
    """Return empty metrics structure."""
    return {
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0,
        'total_pnl': 0,
        'total_commission': 0,
        'net_profit': 0,
        'gross_profit': 0,
        'gross_loss': 0,
        'profit_factor': 0,
        'avg_trade': 0,
        'avg_win': 0,
        'avg_loss': 0,
        'expectancy': 0,
        'total_return': 0,
        'total_return_pct': 0,
        'sharpe_ratio': 0,
        'sortino_ratio': 0,
        'max_drawdown': 0,
        'max_drawdown_pct': 0,
        'max_drawdown_dollar': 0,
        'calmar_ratio': 0,
        'max_consecutive_wins': 0,
        'max_consecutive_losses': 0,
        'risk_of_ruin': 0,
        'best_month': 0,
        'worst_month': 0,
        'monthly_std': 0,
    }


def format_metrics(metrics: Dict) -> str:
    """Format metrics as a readable string."""
    return f"""
Performance Metrics
{'='*50}
Trade Statistics:
  Total Trades: {metrics['total_trades']}
  Win Rate: {metrics['win_rate']:.1%}
  Winning Trades: {metrics['winning_trades']}
  Losing Trades: {metrics['losing_trades']}
  Max Consecutive Wins: {metrics['max_consecutive_wins']}
  Max Consecutive Losses: {metrics['max_consecutive_losses']}

Profit & Loss:
  Gross Profit: ${metrics['gross_profit']:,.2f}
  Gross Loss: ${metrics['gross_loss']:,.2f}
  Net Profit: ${metrics['net_profit']:,.2f}
  Total Commissions: ${metrics['total_commission']:,.2f}
  Total Return: {metrics['total_return']:.2%}

Trade Metrics:
  Average Trade: ${metrics['avg_trade']:,.2f}
  Average Win: ${metrics['avg_win']:,.2f}
  Average Loss: ${metrics['avg_loss']:,.2f}
  Profit Factor: {metrics['profit_factor']:.2f}
  Expectancy: ${metrics['expectancy']:,.2f}

Risk Metrics:
  Max Drawdown: {metrics['max_drawdown']:.2%} (${metrics['max_drawdown_dollar']:,.2f})
  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
  Sortino Ratio: {metrics['sortino_ratio']:.2f}
  Calmar Ratio: {metrics['calmar_ratio']:.2f}
  Risk of Ruin: {metrics['risk_of_ruin']:.2%}

Monthly Performance:
  Best Month: {metrics['best_month']:.2%}
  Worst Month: {metrics['worst_month']:.2%}
  Monthly Std Dev: {metrics['monthly_std']:.2%}
"""
