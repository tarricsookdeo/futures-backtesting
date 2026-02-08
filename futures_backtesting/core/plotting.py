"""
Interactive plotting for backtest results.
"""
from typing import List, Dict, Optional
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_equity_curve(equity_curve: List[Dict], trades: Optional[List[Dict]] = None,
                     title: str = "Backtest Results") -> go.Figure:
    """
    Create interactive equity curve plot.
    
    Args:
        equity_curve: List of equity curve points
        trades: Optional list of trades to mark on chart
        title: Plot title
        
    Returns:
        Plotly figure
    """
    # Convert to DataFrame
    df = pd.DataFrame(equity_curve)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Create figure with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(title, "Drawdown")
    )
    
    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['equity'],
            name='Equity',
            line=dict(color='#2E86AB', width=2),
            hovertemplate='%{x}<br>Equity: $%{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Cash line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['cash'],
            name='Cash',
            line=dict(color='#A23B72', width=1, dash='dash'),
            opacity=0.7,
            hovertemplate='%{x}<br>Cash: $%{y:,.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Add trade markers if provided
    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        
        # Winning trades
        wins = trades_df[trades_df['net_pnl'] > 0]
        if len(wins) > 0:
            fig.add_trace(
                go.Scatter(
                    x=wins['timestamp'],
                    y=[df['equity'].reindex(ts, method='ffill') for ts in wins['timestamp']],
                    mode='markers',
                    name='Winning Trade',
                    marker=dict(color='#28A745', size=10, symbol='triangle-up'),
                    hovertemplate='%{x}<br>Win: $%{text:,.2f}<extra></extra>',
                    text=wins['net_pnl']
                ),
                row=1, col=1
            )
        
        # Losing trades
        losses = trades_df[trades_df['net_pnl'] < 0]
        if len(losses) > 0:
            fig.add_trace(
                go.Scatter(
                    x=losses['timestamp'],
                    y=[df['equity'].reindex(ts, method='ffill') for ts in losses['timestamp']],
                    mode='markers',
                    name='Losing Trade',
                    marker=dict(color='#DC3545', size=10, symbol='triangle-down'),
                    hovertemplate='%{x}<br>Loss: $%{text:,.2f}<extra></extra>',
                    text=losses['net_pnl']
                ),
                row=1, col=1
            )
    
    # Calculate and plot drawdown
    peak = df['equity'].expanding().max()
    drawdown = (df['equity'] - peak) / peak * 100
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=drawdown,
            name='Drawdown %',
            fill='tozeroy',
            fillcolor='rgba(220, 53, 69, 0.3)',
            line=dict(color='#DC3545', width=1),
            hovertemplate='%{x}<br>Drawdown: %{y:.2f}%<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Layout
    fig.update_layout(
        height=700,
        showlegend=True,
        hovermode='x unified',
        template='plotly_white',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    fig.update_yaxes(title_text='Equity ($)', row=1, col=1)
    fig.update_yaxes(title_text='Drawdown (%)', row=2, col=1)
    fig.update_xaxes(title_text='Date', row=2, col=1)
    
    return fig


def plot_monthly_returns(equity_curve: List[Dict]) -> go.Figure:
    """
    Plot monthly returns heatmap.
    
    Args:
        equity_curve: List of equity curve points
        
    Returns:
        Plotly figure
    """
    df = pd.DataFrame(equity_curve)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Calculate monthly returns
    monthly = df['equity'].resample('ME').last()
    monthly_returns = monthly.pct_change() * 100
    
    # Create year-month breakdown
    monthly_data = monthly_returns.to_frame()
    monthly_data['Year'] = monthly_data.index.year
    monthly_data['Month'] = monthly_data.index.month
    monthly_data['MonthName'] = monthly_data.index.strftime('%b')
    
    # Pivot for heatmap
    pivot = monthly_data.pivot(index='Year', columns='Month', values='equity')
    pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:len(pivot.columns)]
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=[
            [0, '#DC3545'],
            [0.5, '#FFFFFF'],
            [1, '#28A745']
        ],
        zmid=0,
        text=[[f'{v:.1f}%' if not pd.isna(v) else '' for v in row] for row in pivot.values],
        texttemplate='%{text}',
        hovertemplate='%{y} %{x}<br>Return: %{z:.2f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='Monthly Returns (%)',
        height=400,
        template='plotly_white',
        yaxis_title='Year',
        xaxis_title='Month'
    )
    
    return fig


def plot_trade_distribution(trades: List[Dict]) -> go.Figure:
    """
    Plot trade P&L distribution.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        Plotly figure
    """
    if not trades:
        return go.Figure()
    
    df = pd.DataFrame(trades)
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Trade P&L Distribution', 'Cumulative P&L',
                       'P&L by Symbol', 'Win/Loss Ratio'),
        specs=[
            [{}, {}],
            [{}, {'type': 'domain'}]
        ]
    )
    
    # 1. Histogram of P&L
    colors = ['#28A745' if x > 0 else '#DC3545' for x in df['net_pnl']]
    fig.add_trace(
        go.Histogram(
            x=df['net_pnl'],
            name='Trade P&L',
            marker_color=colors,
            opacity=0.7,
            nbinsx=30,
            hovertemplate='$%{x:,.2f}<br>Count: %{y}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # 2. Cumulative P&L
    df_sorted = df.sort_values('timestamp')
    df_sorted['cumulative'] = df_sorted['net_pnl'].cumsum()
    fig.add_trace(
        go.Scatter(
            x=df_sorted['timestamp'],
            y=df_sorted['cumulative'],
            name='Cumulative P&L',
            fill='tozeroy',
            line=dict(color='#2E86AB'),
            hovertemplate='%{x}<br>Cumulative: $%{y:,.2f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # 3. P&L by symbol
    symbol_pnl = df.groupby('symbol')['net_pnl'].sum().sort_values(ascending=True)
    colors = ['#28A745' if x > 0 else '#DC3545' for x in symbol_pnl.values]
    fig.add_trace(
        go.Bar(
            x=symbol_pnl.values,
            y=symbol_pnl.index,
            orientation='h',
            name='By Symbol',
            marker_color=colors,
            hovertemplate='%{y}<br>P&L: $%{x:,.2f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # 4. Win/Loss pie chart
    wins = len(df[df['net_pnl'] > 0])
    losses = len(df[df['net_pnl'] < 0])
    fig.add_trace(
        go.Pie(
            labels=['Wins', 'Losses'],
            values=[wins, losses],
            marker_colors=['#28A745', '#DC3545'],
            textinfo='label+percent',
            hovertemplate='%{label}<br>Count: %{value}<br>Percent: %{percent}<extra></extra>'
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        height=700,
        showlegend=False,
        template='plotly_white'
    )
    
    return fig


def create_full_report(results, title: str = "Backtest Report") -> go.Figure:
    """
    Create a comprehensive backtest report with multiple charts.
    
    Args:
        results: BacktestResult object
        title: Report title
        
    Returns:
        Plotly figure
    """
    if not results.equity_curve:
        return go.Figure()
    
    # Create tabs
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(title, 'Monthly Returns', 'Trade Analysis'),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    # This is a simplified version - in practice you'd use dash or tabs
    # For now, return the main equity curve
    return plot_equity_curve(results.equity_curve, results.trades, title)


def plot_ohlc_with_trades(data, trades: List[Dict], symbol: str) -> go.Figure:
    """
    Plot OHLC chart with trade entries and exits.
    
    Args:
        data: DataFeed or DataFrame with OHLC data
        trades: List of trades
        symbol: Symbol to plot
        
    Returns:
        Plotly figure
    """
    # Get OHLC data
    if hasattr(data, 'data'):
        df = data.data.copy()
    else:
        df = data.copy()
    
    # Create figure
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Price'
    ))
    
    # Add trade markers
    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df = trades_df[trades_df['symbol'] == symbol]
        
        for _, trade in trades_df.iterrows():
            color = '#28A745' if trade['net_pnl'] > 0 else '#DC3545'
            
            # Entry marker
            fig.add_trace(go.Scatter(
                x=[trade['timestamp']],
                y=[trade['entry_price']],
                mode='markers',
                marker=dict(color=color, size=12, symbol='arrow-up' if trade['side'] == 'LONG' else 'arrow-down'),
                name=f"Entry ({trade['side']})",
                showlegend=False,
                hovertemplate=f"Entry<br>Price: ${trade['entry_price']:.2f}<extra></extra>"
            ))
    
    fig.update_layout(
        title=f'{symbol} Price with Trades',
        yaxis_title='Price',
        xaxis_title='Date',
        height=600,
        template='plotly_white'
    )
    
    return fig
