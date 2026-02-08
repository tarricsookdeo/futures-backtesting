"""
Trade journal and export functionality.
"""
import pandas as pd
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
import uuid


@dataclass
class TradeJournalEntry:
    """
    Comprehensive trade journal entry.
    
    Tracks all aspects of a trade for post-analysis.
    """
    # Basic trade info
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    symbol: str = ""
    side: str = ""  # 'LONG' or 'SHORT'
    size: int = 0
    
    # Prices
    entry_price: float = 0.0
    exit_price: float = 0.0
    
    # P&L
    gross_pnl: float = 0.0
    commission: float = 0.0
    net_pnl: float = 0.0
    
    # Risk metrics
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    initial_risk: float = 0.0  # Dollar risk at entry
    r_multiple: float = 0.0    # P&L expressed in R multiples
    
    # Trade management
    max_favorable_excursion: float = 0.0   # Max profit during trade
    max_adverse_excursion: float = 0.0     # Max drawdown during trade
    exit_efficiency: float = 0.0           # How well exit was timed (0-1)
    
    # Context
    setup_type: str = ""           # e.g., 'breakout', 'mean_reversion', 'trend_following'
    market_condition: str = ""     # e.g., 'trending_up', 'ranging', 'volatile'
    session: str = ""              # e.g., 'london', 'ny_am', 'ny_pm', 'asia'
    
    # Analysis
    entry_quality: Optional[int] = None    # 1-10 rating
    exit_quality: Optional[int] = None     # 1-10 rating
    followed_plan: Optional[bool] = None   # Did you follow your trading plan?
    emotions: str = ""             # How you felt during the trade
    mistakes: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    
    # Screenshots
    entry_screenshot: str = ""     # Path to entry screenshot
    exit_screenshot: str = ""      # Path to exit screenshot
    
    # Technical context
    market_structure: str = ""     # e.g., 'higher_high', 'lower_low'
    volume_profile: str = ""       # e.g., 'high_volume', 'low_volume'
    key_levels_nearby: List[float] = field(default_factory=list)
    
    # Notes
    pre_trade_notes: str = ""
    post_trade_notes: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived fields."""
        if self.net_pnl == 0 and self.gross_pnl != 0:
            self.net_pnl = self.gross_pnl - self.commission
        
        # Calculate duration
        if self.entry_time and self.exit_time:
            self.duration = self.exit_time - self.entry_time
        else:
            self.duration = None
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Trade duration in minutes."""
        if self.entry_time and self.exit_time:
            return (self.exit_time - self.entry_time).total_seconds() / 60
        return None
    
    @property
    def is_winner(self) -> bool:
        """True if trade was profitable."""
        return self.net_pnl > 0
    
    @property
    def risk_reward_ratio(self) -> float:
        """Actual R:R ratio achieved."""
        if self.initial_risk > 0:
            return abs(self.net_pnl) / self.initial_risk
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to strings
        for key in ['entry_time', 'exit_time', 'created_at']:
            if data[key]:
                data[key] = data[key].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeJournalEntry':
        """Create from dictionary."""
        # Convert string timestamps back to datetime
        for key in ['entry_time', 'exit_time', 'created_at']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class TradeJournal:
    """
    Trade journal for tracking and analyzing trades.
    """
    
    def __init__(self, name: str = "My Trading Journal"):
        self.name = name
        self.entries: Dict[str, TradeJournalEntry] = {}
        self.stats: Dict[str, Any] = {}
    
    def add_entry(self, entry: TradeJournalEntry) -> str:
        """Add a trade entry to the journal."""
        self.entries[entry.trade_id] = entry
        return entry.trade_id
    
    def get_entry(self, trade_id: str) -> Optional[TradeJournalEntry]:
        """Get a specific trade entry."""
        return self.entries.get(trade_id)
    
    def update_entry(self, trade_id: str, **kwargs):
        """Update an existing entry."""
        if trade_id in self.entries:
            entry = self.entries[trade_id]
            for key, value in kwargs.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
    
    def delete_entry(self, trade_id: str) -> bool:
        """Delete a trade entry."""
        if trade_id in self.entries:
            del self.entries[trade_id]
            return True
        return False
    
    def get_entries(self, 
                   symbol: Optional[str] = None,
                   setup_type: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   min_pnl: Optional[float] = None,
                   max_pnl: Optional[float] = None,
                   tags: Optional[List[str]] = None) -> List[TradeJournalEntry]:
        """
        Filter entries based on criteria.
        """
        results = list(self.entries.values())
        
        if symbol:
            results = [e for e in results if e.symbol == symbol]
        
        if setup_type:
            results = [e for e in results if e.setup_type == setup_type]
        
        if start_date:
            results = [e for e in results if e.entry_time and e.entry_time >= start_date]
        
        if end_date:
            results = [e for e in results if e.entry_time and e.entry_time <= end_date]
        
        if min_pnl is not None:
            results = [e for e in results if e.net_pnl >= min_pnl]
        
        if max_pnl is not None:
            results = [e for e in results if e.net_pnl <= max_pnl]
        
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        
        return sorted(results, key=lambda x: x.entry_time or datetime.min)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert all entries to a DataFrame."""
        if not self.entries:
            return pd.DataFrame()
        
        data = [e.to_dict() for e in self.entries.values()]
        df = pd.DataFrame(data)
        
        # Sort by entry time
        if 'entry_time' in df.columns:
            df['entry_time'] = pd.to_datetime(df['entry_time'])
            df.sort_values('entry_time', inplace=True)
        
        return df
    
    def export_csv(self, filepath: Union[str, Path]):
        """Export journal to CSV."""
        df = self.to_dataframe()
        df.to_csv(filepath, index=False)
    
    def export_json(self, filepath: Union[str, Path]):
        """Export journal to JSON."""
        data = {
            'name': self.name,
            'created_at': datetime.now().isoformat(),
            'entries': [e.to_dict() for e in self.entries.values()]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    @classmethod
    def load_json(cls, filepath: Union[str, Path]) -> 'TradeJournal':
        """Load journal from JSON."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        journal = cls(name=data.get('name', 'Imported Journal'))
        
        for entry_data in data.get('entries', []):
            entry = TradeJournalEntry.from_dict(entry_data)
            journal.add_entry(entry)
        
        return journal
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate journal statistics."""
        if not self.entries:
            return {}
        
        df = self.to_dataframe()
        
        # Basic stats
        total_trades = len(df)
        winning_trades = len(df[df['net_pnl'] > 0])
        losing_trades = len(df[df['net_pnl'] < 0])
        
        stats = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_pnl': df['net_pnl'].sum(),
            'avg_pnl': df['net_pnl'].mean(),
            'avg_win': df[df['net_pnl'] > 0]['net_pnl'].mean() if winning_trades > 0 else 0,
            'avg_loss': df[df['net_pnl'] < 0]['net_pnl'].mean() if losing_trades > 0 else 0,
        }
        
        # Setup type performance
        if 'setup_type' in df.columns:
            setup_stats = df.groupby('setup_type')['net_pnl'].agg(['count', 'sum', 'mean'])
            stats['by_setup'] = setup_stats.to_dict()
        
        # Symbol performance
        if 'symbol' in df.columns:
            symbol_stats = df.groupby('symbol')['net_pnl'].agg(['count', 'sum', 'mean'])
            stats['by_symbol'] = symbol_stats.to_dict()
        
        # Session performance
        if 'session' in df.columns:
            session_stats = df.groupby('session')['net_pnl'].agg(['count', 'sum', 'mean'])
            stats['by_session'] = session_stats.to_dict()
        
        return stats
    
    def print_summary(self):
        """Print journal summary."""
        stats = self.get_statistics()
        
        if not stats:
            print("No trades in journal.")
            return
        
        print(f"\n{'='*60}")
        print(f"Trade Journal: {self.name}")
        print(f"{'='*60}")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Win Rate: {stats['win_rate']:.1%}")
        print(f"Total P&L: ${stats['total_pnl']:,.2f}")
        print(f"Avg Trade: ${stats['avg_pnl']:,.2f}")
        print(f"Avg Win: ${stats['avg_win']:,.2f}")
        print(f"Avg Loss: ${stats['avg_loss']:,.2f}")
        
        if 'by_setup' in stats:
            print(f"\n{'-'*60}")
            print("Performance by Setup:")
            for setup, data in stats['by_setup'].items():
                print(f"  {setup}: {data['count']} trades, ${data['sum']:,.2f}")


class TradeJournalExporter:
    """Export trade data in various formats."""
    
    @staticmethod
    def to_csv(trades: List[Dict], filepath: Union[str, Path]):
        """Export trades to CSV."""
        df = pd.DataFrame(trades)
        df.to_csv(filepath, index=False)
        print(f"Exported {len(trades)} trades to {filepath}")
    
    @staticmethod
    def to_excel(trades: List[Dict], filepath: Union[str, Path]):
        """Export trades to Excel with formatting."""
        df = pd.DataFrame(trades)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Trades', index=False)
            
            # Add summary sheet
            summary = TradeJournalExporter._create_summary(df)
            summary.to_excel(writer, sheet_name='Summary')
        
        print(f"Exported {len(trades)} trades to {filepath}")
    
    @staticmethod
    def to_json(trades: List[Dict], filepath: Union[str, Path]):
        """Export trades to JSON."""
        with open(filepath, 'w') as f:
            json.dump(trades, f, indent=2, default=str)
        print(f"Exported {len(trades)} trades to {filepath}")
    
    @staticmethod
    def _create_summary(df: pd.DataFrame) -> pd.DataFrame:
        """Create summary statistics."""
        summary = {
            'Metric': ['Total Trades', 'Winning Trades', 'Losing Trades', 
                      'Win Rate', 'Total P&L', 'Avg Trade', 'Avg Win', 'Avg Loss',
                      'Max Win', 'Max Loss', 'Profit Factor'],
            'Value': [
                len(df),
                len(df[df['net_pnl'] > 0]),
                len(df[df['net_pnl'] < 0]),
                f"{len(df[df['net_pnl'] > 0]) / len(df):.1%}",
                f"${df['net_pnl'].sum():,.2f}",
                f"${df['net_pnl'].mean():,.2f}",
                f"${df[df['net_pnl'] > 0]['net_pnl'].mean():,.2f}",
                f"${df[df['net_pnl'] < 0]['net_pnl'].mean():,.2f}",
                f"${df['net_pnl'].max():,.2f}",
                f"${df['net_pnl'].min():,.2f}",
                f"{abs(df[df['net_pnl'] > 0]['net_pnl'].sum() / df[df['net_pnl'] < 0]['net_pnl'].sum()):.2f}"
                if len(df[df['net_pnl'] < 0]) > 0 else 'N/A'
            ]
        }
        return pd.DataFrame(summary)


# Convenience functions
def create_trade_journal(name: str = "My Journal") -> TradeJournal:
    """Create a new trade journal."""
    return TradeJournal(name)


def load_journal(filepath: Union[str, Path]) -> TradeJournal:
    """Load a trade journal from file."""
    suffix = Path(filepath).suffix.lower()
    
    if suffix == '.json':
        return TradeJournal.load_json(filepath)
    else:
        raise ValueError(f"Unsupported format: {suffix}")
