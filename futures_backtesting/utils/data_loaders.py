"""
Data loaders for various formats.
"""
import pandas as pd
import numpy as np
from typing import Optional, Union, List
from pathlib import Path
import json


class TradingViewLoader:
    """
    Load data from TradingView CSV exports.
    
    TradingView exports typically have columns:
    - time, open, high, low, close, Volume, Volume MA
    - or: time, open, high, low, close, Volume
    """
    
    @staticmethod
    def load(filepath: Union[str, Path], 
             symbol: Optional[str] = None,
             timeframe: Optional[str] = None) -> pd.DataFrame:
        """
        Load TradingView CSV data.
        
        Args:
            filepath: Path to CSV file
            symbol: Symbol name (auto-detected from filename if not provided)
            timeframe: Timeframe string (auto-detected if not provided)
            
        Returns:
            DataFrame with standard OHLCV columns and DatetimeIndex
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Try to detect symbol from filename
        if symbol is None:
            symbol = TradingViewLoader._detect_symbol(filepath.name)
        
        # Try to detect timeframe from filename
        if timeframe is None:
            timeframe = TradingViewLoader._detect_timeframe(filepath.name)
        
        # Read CSV
        df = pd.read_csv(filepath)
        
        # Standardize column names
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Handle different time column names
        time_col = None
        for col in ['time', 'datetime', 'date', 'timestamp']:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            raise ValueError(f"Could not find time column in {df.columns.tolist()}")
        
        # Parse datetime
        df[time_col] = pd.to_datetime(df[time_col])
        df.set_index(time_col, inplace=True)
        
        # Standardize OHLCV columns
        column_mapping = {}
        for col in df.columns:
            if col in ['open', 'o']:
                column_mapping[col] = 'open'
            elif col in ['high', 'h']:
                column_mapping[col] = 'high'
            elif col in ['low', 'l']:
                column_mapping[col] = 'low'
            elif col in ['close', 'c']:
                column_mapping[col] = 'close'
            elif col in ['volume', 'vol', 'v', 'volume MA']:
                column_mapping[col] = 'volume'
        
        df.rename(columns=column_mapping, inplace=True)
        
        # Ensure required columns exist
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Ensure OHLC relationships are valid
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)
        
        # Sort by index
        df.sort_index(inplace=True)
        
        # Add metadata
        df.attrs['symbol'] = symbol
        df.attrs['timeframe'] = timeframe
        df.attrs['source'] = 'tradingview'
        
        return df[required]
    
    @staticmethod
    def _detect_symbol(filename: str) -> Optional[str]:
        """Try to detect symbol from filename."""
        # Common patterns: MES1!, MNQ1!, SPY, AAPL, etc.
        import re
        
        # Look for futures patterns
        futures_match = re.search(r'(MES|MNQ|MGC|MYM|ES|NQ|GC|YM)[12]?!?', filename.upper())
        if futures_match:
            return futures_match.group(1)
        
        # Look for stock/crypto patterns (2-5 uppercase letters)
        stock_match = re.search(r'([A-Z]{2,5})', filename.upper())
        if stock_match:
            return stock_match.group(1)
        
        return None
    
    @staticmethod
    def _detect_timeframe(filename: str) -> Optional[str]:
        """Try to detect timeframe from filename."""
        import re
        
        filename_upper = filename.upper()
        
        # Common patterns
        patterns = [
            (r'1M(?!A)', '1min'),
            (r'5M(?!A)', '5min'),
            (r'15M(?!A)', '15min'),
            (r'30M(?!A)', '30min'),
            (r'1H', '1h'),
            (r'4H', '4h'),
            (r'D(?!A)', '1d'),
            (r'W(?!A)', '1w'),
        ]
        
        for pattern, tf in patterns:
            if re.search(pattern, filename_upper):
                return tf
        
        return None


class GenericCSVLoader:
    """Generic CSV loader with auto-detection."""
    
    @staticmethod
    def load(filepath: Union[str, Path],
             datetime_col: Optional[str] = None,
             column_mapping: Optional[dict] = None,
             symbol: Optional[str] = None,
             timeframe: Optional[str] = None) -> pd.DataFrame:
        """
        Load generic CSV with configurable column mapping.
        
        Args:
            filepath: Path to CSV
            datetime_col: Name of datetime column
            column_mapping: Dict mapping file columns to standard names
            symbol: Symbol name
            timeframe: Timeframe string
        """
        filepath = Path(filepath)
        df = pd.read_csv(filepath)
        
        # Auto-detect datetime column
        if datetime_col is None:
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['time', 'date', 'timestamp']):
                    datetime_col = col
                    break
        
        if datetime_col is None:
            raise ValueError("Could not detect datetime column")
        
        # Parse datetime
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df.set_index(datetime_col, inplace=True)
        
        # Apply column mapping
        if column_mapping:
            df.rename(columns=column_mapping, inplace=True)
        else:
            # Auto-map common variations
            auto_map = {}
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower in ['open', 'o']:
                    auto_map[col] = 'open'
                elif col_lower in ['high', 'h']:
                    auto_map[col] = 'high'
                elif col_lower in ['low', 'l']:
                    auto_map[col] = 'low'
                elif col_lower in ['close', 'c', 'last']:
                    auto_map[col] = 'close'
                elif col_lower in ['volume', 'vol', 'v', 'qty']:
                    auto_map[col] = 'volume'
            df.rename(columns=auto_map, inplace=True)
        
        # Ensure required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                df[col] = 0  # Default to 0 if missing
        
        # Fix OHLC relationships
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)
        
        df.sort_index(inplace=True)
        
        df.attrs['symbol'] = symbol
        df.attrs['timeframe'] = timeframe
        df.attrs['source'] = 'generic_csv'
        
        return df[required]


class ParquetLoader:
    """Load data from Parquet format (fast for large datasets)."""
    
    @staticmethod
    def load(filepath: Union[str, Path],
             symbol: Optional[str] = None,
             timeframe: Optional[str] = None) -> pd.DataFrame:
        """Load OHLCV data from Parquet file."""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        df = pd.read_parquet(filepath)
        
        # Ensure DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
        
        # Standardize columns
        required = ['open', 'high', 'low', 'close', 'volume']
        df.columns = [c.lower() for c in df.columns]
        
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        df.attrs['symbol'] = symbol
        df.attrs['timeframe'] = timeframe
        df.attrs['source'] = 'parquet'
        
        return df[required]
    
    @staticmethod
    def save(df: pd.DataFrame, filepath: Union[str, Path],
             compression: str = 'zstd'):
        """Save DataFrame to Parquet format."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(filepath, compression=compression)


class DataLoader:
    """Unified data loader with auto-detection."""
    
    @staticmethod
    def load(filepath: Union[str, Path], **kwargs) -> pd.DataFrame:
        """
        Load data from file with auto-detection of format.
        
        Args:
            filepath: Path to data file
            **kwargs: Additional arguments passed to specific loader
            
        Returns:
            DataFrame with OHLCV data
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        suffix = filepath.suffix.lower()
        
        if suffix == '.csv':
            return TradingViewLoader.load(filepath, **kwargs)
        elif suffix == '.parquet' or suffix == '.pq':
            return ParquetLoader.load(filepath, **kwargs)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    @staticmethod
    def load_multiple(filepaths: List[Union[str, Path]],
                     symbols: Optional[List[str]] = None) -> 'MultiDataFeed':
        """
        Load multiple data files into a MultiDataFeed.
        
        Args:
            filepaths: List of file paths
            symbols: Optional list of symbols (auto-detected if not provided)
            
        Returns:
            MultiDataFeed with all data
        """
        from ..core.data import MultiDataFeed
        
        feed = MultiDataFeed()
        
        for i, filepath in enumerate(filepaths):
            df = DataLoader.load(filepath)
            
            # Get symbol
            if symbols and i < len(symbols):
                symbol = symbols[i]
            else:
                symbol = df.attrs.get('symbol', f'SYMBOL_{i}')
            
            # Get timeframe
            timeframe = df.attrs.get('timeframe', '1min')
            
            feed.add_data(df, symbol, timeframe)
        
        return feed


def load_tradingview(filepath: str, symbol: Optional[str] = None) -> pd.DataFrame:
    """Convenience function to load TradingView CSV."""
    return TradingViewLoader.load(filepath, symbol=symbol)


def load_parquet(filepath: str) -> pd.DataFrame:
    """Convenience function to load Parquet file."""
    return ParquetLoader.load(filepath)
