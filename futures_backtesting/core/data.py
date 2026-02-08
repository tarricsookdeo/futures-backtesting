"""
Data handling for OHLCV data.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Union
from datetime import datetime


class DataFeed:
    """Data feed for a single instrument."""
    
    def __init__(self, data: pd.DataFrame, symbol: str, timeframe: str = "1min"):
        """
        Initialize data feed.
        
        Args:
            data: DataFrame with OHLCV data and datetime index
            symbol: Instrument symbol
            timeframe: Timeframe string (e.g., "1min", "5min", "15min")
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.data = self._validate_data(data)
        self._idx = 0
        
    def _validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate and standardize data format."""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        
        # Convert column names to lowercase
        data.columns = [c.lower() for c in data.columns]
        
        # Check required columns
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"Data must contain '{col}' column")
        
        # Ensure datetime index
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data must have a DatetimeIndex")
        
        # Sort by index
        data = data.sort_index()
        
        return data[required_cols]
    
    def __len__(self):
        return len(self.data)
    
    def __iter__(self):
        self._idx = 0
        return self
    
    def __next__(self):
        if self._idx >= len(self.data):
            raise StopIteration
        row = self.data.iloc[self._idx]
        timestamp = self.data.index[self._idx]
        self._idx += 1
        return timestamp, row
    
    def get(self, idx: int) -> tuple:
        """Get data at specific index."""
        if idx < 0 or idx >= len(self.data):
            raise IndexError(f"Index {idx} out of range")
        return self.data.index[idx], self.data.iloc[idx]
    
    def current(self) -> tuple:
        """Get current data point."""
        return self.get(self._idx)
    
    def reset(self):
        """Reset iterator to beginning."""
        self._idx = 0
    
    @property
    def datetime(self) -> pd.DatetimeIndex:
        """Get datetime index."""
        return self.data.index
    
    def get_range(self, start: int, end: int) -> pd.DataFrame:
        """Get data range."""
        return self.data.iloc[start:end]
    
    def get_until(self, timestamp: datetime) -> pd.DataFrame:
        """Get all data up to timestamp."""
        return self.data[self.data.index <= timestamp]


class MultiDataFeed:
    """Multiple data feeds with synchronization."""
    
    def __init__(self):
        self._feeds: Dict[str, DataFeed] = {}
        self._timeframes: Dict[str, str] = {}
        
    def add_data(self, data: pd.DataFrame, symbol: str, timeframe: str = "1min"):
        """Add a data feed."""
        self._feeds[symbol] = DataFeed(data, symbol, timeframe)
        self._timeframes[symbol] = timeframe
        
    def get_feed(self, symbol: str) -> DataFeed:
        """Get a specific data feed."""
        if symbol not in self._feeds:
            raise ValueError(f"No data feed for symbol: {symbol}")
        return self._feeds[symbol]
    
    def get_symbols(self) -> List[str]:
        """Get all symbols."""
        return list(self._feeds.keys())
    
    def __iter__(self):
        """Iterate through synchronized data."""
        # Find master timeline (earliest start to latest end)
        all_indices = [feed.data.index for feed in self._feeds.values()]
        master_start = min(idx[0] for idx in all_indices)
        master_end = max(idx[-1] for idx in all_indices)
        
        # Create master timeline
        master_index = pd.date_range(start=master_start, end=master_end, freq='1min')
        
        for timestamp in master_index:
            bar = {}
            for symbol, feed in self._feeds.items():
                # Find closest data point not exceeding timestamp
                valid_data = feed.data[feed.data.index <= timestamp]
                if len(valid_data) > 0:
                    bar[symbol] = valid_data.iloc[-1]
            
            if bar:  # Only yield if we have data for at least one symbol
                yield timestamp, bar
    
    def __len__(self):
        """Return length of longest feed."""
        return max(len(feed) for feed in self._feeds.values()) if self._feeds else 0
