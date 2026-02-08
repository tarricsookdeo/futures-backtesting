"""
Base strategy class modeled after Backtrader.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Callable
from datetime import datetime
import pandas as pd

from .data import DataFeed, MultiDataFeed
from .orders import Order, OrderType, OrderSide
from ..contracts.micros import get_contract


class BaseStrategy(ABC):
    """
    Base strategy class. Subclass this to create your own strategies.
    
    Similar to backtrader's Strategy class.
    """
    
    def __init__(self):
        self.broker = None  # Set by backtest engine
        self.data: MultiDataFeed = None  # Set by backtest engine
        self._indicators: Dict = {}
        
    def initialize(self):
        """
        Called once at the beginning of the backtest.
        Use this to set up indicators, etc.
        """
        pass
    
    @abstractmethod
    def next(self):
        """
        Called for each new bar.
        This is where you implement your trading logic.
        """
        pass
    
    def notify_order(self, order: Order):
        """
        Called when an order status changes.
        Override to handle order updates.
        """
        pass
    
    def notify_trade(self, symbol: str, size: int, entry_price: float, 
                     exit_price: float, pnl: float):
        """
        Called when a trade is completed.
        Override to handle trade completions.
        """
        pass
    
    # Data access helpers
    def get_data(self, symbol: str) -> DataFeed:
        """Get data feed for a symbol."""
        return self.data.get_feed(symbol)
    
    def get_close(self, symbol: str) -> float:
        """Get current close price."""
        feed = self.get_data(symbol)
        _, bar = feed.current()
        return bar['close']
    
    def get_open(self, symbol: str) -> float:
        """Get current open price."""
        feed = self.get_data(symbol)
        _, bar = feed.current()
        return bar['open']
    
    def get_high(self, symbol: str) -> float:
        """Get current high price."""
        feed = self.get_data(symbol)
        _, bar = feed.current()
        return bar['high']
    
    def get_low(self, symbol: str) -> float:
        """Get current low price."""
        feed = self.get_data(symbol)
        _, bar = feed.current()
        return bar['low']
    
    def get_volume(self, symbol: str) -> float:
        """Get current volume."""
        feed = self.get_data(symbol)
        _, bar = feed.current()
        return bar['volume']
    
    def get_datetime(self) -> datetime:
        """Get current datetime."""
        for feed in self.data._feeds.values():
            ts, _ = feed.current()
            return ts
        return None
    
    def get_position(self, symbol: str) -> int:
        """Get current position size for symbol."""
        if self.broker is None:
            return 0
        position = self.broker.get_position(symbol)
        return position.size
    
    def get_position_value(self, symbol: str) -> float:
        """Get current position value (unrealized P&L not included)."""
        if self.broker is None:
            return 0.0
        position = self.broker.get_position(symbol)
        return position.size * position.avg_entry_price
    
    # Order placement helpers
    def buy(self, symbol: str, size: int = 1, price: Optional[float] = None,
            stop_price: Optional[float] = None, exectype: OrderType = OrderType.MARKET) -> str:
        """
        Place a buy order.
        
        Args:
            symbol: Symbol to buy
            size: Number of contracts
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            exectype: Order type
        """
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            size=size,
            order_type=exectype,
            price=price,
            stop_price=stop_price,
            timestamp=self.get_datetime()
        )
        return self.broker.submit_order(order)
    
    def sell(self, symbol: str, size: int = 1, price: Optional[float] = None,
             stop_price: Optional[float] = None, exectype: OrderType = OrderType.MARKET) -> str:
        """
        Place a sell order.
        
        Args:
            symbol: Symbol to sell
            size: Number of contracts
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            exectype: Order type
        """
        order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            size=size,
            order_type=exectype,
            price=price,
            stop_price=stop_price,
            timestamp=self.get_datetime()
        )
        return self.broker.submit_order(order)
    
    def close(self, symbol: str) -> Optional[str]:
        """
        Close position for a symbol.
        Returns order ID if position was closed, None if no position.
        """
        position = self.broker.get_position(symbol)
        if position.is_flat():
            return None
        
        if position.is_long():
            return self.sell(symbol, size=position.size)
        else:
            return self.buy(symbol, size=abs(position.size))
    
    def close_all(self) -> List[str]:
        """Close all positions. Returns list of order IDs."""
        order_ids = []
        for symbol in self.data.get_symbols():
            order_id = self.close(symbol)
            if order_id:
                order_ids.append(order_id)
        return order_ids
    
    def buy_bracket(self, symbol: str, size: int = 1,
                    take_profit_ticks: int = 20,
                    stop_loss_ticks: int = 10,
                    price: Optional[float] = None,
                    exectype: OrderType = OrderType.MARKET) -> tuple:
        """
        Place a buy bracket order with entry, take profit, and stop loss.
        
        The take profit and stop loss are linked as an OCO pair (One-Cancels-Other).
        When one fills, the other is automatically cancelled.
        
        Args:
            symbol: Symbol to trade
            size: Number of contracts
            take_profit_ticks: Number of ticks for take profit (above entry for longs)
            stop_loss_ticks: Number of ticks for stop loss (below entry for longs)
            price: Entry price (for limit/stop entries)
            exectype: Entry order type
            
        Returns:
            Tuple of (entry_order_id, tp_order_id, sl_order_id)
        """
        # Get contract specs for tick size
        contract = get_contract(symbol)
        tick_size = contract.tick_size
        
        # Determine entry price for calculating TP/SL
        entry_price = price if price is not None else self.get_close(symbol)
        
        # Calculate take profit price (above entry for long)
        tp_price = entry_price + (take_profit_ticks * tick_size)
        
        # Calculate stop loss price (below entry for long)
        sl_price = entry_price - (stop_loss_ticks * tick_size)
        
        # Create entry order
        entry_order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            size=size,
            order_type=exectype,
            price=price,
            timestamp=self.get_datetime()
        )
        
        # Create take profit order (sell limit at TP price)
        tp_order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            size=size,
            order_type=OrderType.LIMIT,
            price=tp_price,
            timestamp=self.get_datetime()
        )
        
        # Create stop loss order (sell stop at SL price)
        sl_order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            size=size,
            order_type=OrderType.STOP,
            stop_price=sl_price,
            timestamp=self.get_datetime()
        )
        
        # Submit as bracket order
        return self.broker.submit_bracket_order(entry_order, tp_order, sl_order)
    
    def sell_bracket(self, symbol: str, size: int = 1,
                     take_profit_ticks: int = 20,
                     stop_loss_ticks: int = 10,
                     price: Optional[float] = None,
                     exectype: OrderType = OrderType.MARKET) -> tuple:
        """
        Place a sell bracket order with entry, take profit, and stop loss.
        
        The take profit and stop loss are linked as an OCO pair (One-Cancels-Other).
        When one fills, the other is automatically cancelled.
        
        Args:
            symbol: Symbol to trade
            size: Number of contracts
            take_profit_ticks: Number of ticks for take profit (below entry for shorts)
            stop_loss_ticks: Number of ticks for stop loss (above entry for shorts)
            price: Entry price (for limit/stop entries)
            exectype: Entry order type
            
        Returns:
            Tuple of (entry_order_id, tp_order_id, sl_order_id)
        """
        # Get contract specs for tick size
        contract = get_contract(symbol)
        tick_size = contract.tick_size
        
        # Determine entry price for calculating TP/SL
        entry_price = price if price is not None else self.get_close(symbol)
        
        # Calculate take profit price (below entry for short)
        tp_price = entry_price - (take_profit_ticks * tick_size)
        
        # Calculate stop loss price (above entry for short)
        sl_price = entry_price + (stop_loss_ticks * tick_size)
        
        # Create entry order
        entry_order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            size=size,
            order_type=exectype,
            price=price,
            timestamp=self.get_datetime()
        )
        
        # Create take profit order (buy limit at TP price)
        tp_order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            size=size,
            order_type=OrderType.LIMIT,
            price=tp_price,
            timestamp=self.get_datetime()
        )
        
        # Create stop loss order (buy stop at SL price)
        sl_order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            size=size,
            order_type=OrderType.STOP,
            stop_price=sl_price,
            timestamp=self.get_datetime()
        )
        
        # Submit as bracket order
        return self.broker.submit_bracket_order(entry_order, tp_order, sl_order)
    
    def cancel(self, order_id: str) -> bool:
        """Cancel an order."""
        return self.broker.cancel_order(order_id)
    
    def cancel_all(self, symbol: Optional[str] = None):
        """Cancel all orders."""
        self.broker.cancel_all(symbol)
    
    # Indicator helpers
    def add_indicator(self, name: str, func: Callable):
        """Add an indicator function."""
        self._indicators[name] = func
    
    def get_indicator(self, name: str, symbol: str):
        """Get indicator value."""
        if name not in self._indicators:
            return None
        return self._indicators[name](symbol)
    
    # Utility methods
    def is_long(self, symbol: str) -> bool:
        """Check if position is long."""
        return self.get_position(symbol) > 0
    
    def is_short(self, symbol: str) -> bool:
        """Check if position is short."""
        return self.get_position(symbol) < 0
    
    def is_flat(self, symbol: str) -> bool:
        """Check if position is flat."""
        return self.get_position(symbol) == 0
