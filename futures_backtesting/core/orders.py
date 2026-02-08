"""
Order types and position management.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
import uuid


class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """Represents a single order."""
    symbol: str
    side: OrderSide
    size: int  # Number of contracts (positive = long, negative = short)
    order_type: OrderType
    
    # Price parameters
    price: Optional[float] = None  # For limit orders
    stop_price: Optional[float] = None  # For stop orders
    
    # Metadata
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: Optional[datetime] = None
    status: OrderStatus = OrderStatus.PENDING
    
    # Fill information
    fill_price: Optional[float] = None
    fill_time: Optional[datetime] = None
    
    # OCO handling
    oco_id: Optional[str] = None  # ID linking OCO orders
    parent_id: Optional[str] = None  # ID of parent order (for brackets)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY
    
    def is_sell(self) -> bool:
        return self.side == OrderSide.SELL
    
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED
    
    def is_active(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.OPEN]
    
    def __repr__(self):
        return f"Order({self.order_id}: {self.side.value} {self.size} {self.symbol} @ {self.price or 'market'})"


@dataclass
class Position:
    """Represents a position in a contract."""
    symbol: str
    size: int = 0  # Positive = long, negative = short
    avg_entry_price: float = 0.0
    
    # Tracking
    trades: List[Dict] = field(default_factory=list)
    
    def update(self, fill_price: float, fill_size: int, timestamp: datetime):
        """Update position with a fill."""
        if self.size == 0:
            # New position
            self.avg_entry_price = fill_price
            self.size = fill_size
        elif self.size * fill_size > 0:
            # Adding to position (same direction)
            total_value = self.size * self.avg_entry_price + fill_size * fill_price
            self.size += fill_size
            self.avg_entry_price = total_value / self.size
        else:
            # Reducing or reversing position
            if abs(fill_size) < abs(self.size):
                # Partial close
                self.size += fill_size  # fill_size is opposite direction
            else:
                # Full close or reversal
                remaining = fill_size + self.size  # Reverse portion
                self.size = remaining
                self.avg_entry_price = fill_price if remaining != 0 else 0.0
        
        self.trades.append({
            'timestamp': timestamp,
            'price': fill_price,
            'size': fill_size,
            'position_after': self.size
        })
    
    def unrealized_pnl(self, current_price: float, tick_value: float, tick_size: float) -> float:
        """Calculate unrealized P&L."""
        if self.size == 0:
            return 0.0
        price_diff = current_price - self.avg_entry_price
        ticks = price_diff / tick_size
        return ticks * tick_value * self.size
    
    def is_long(self) -> bool:
        return self.size > 0
    
    def is_short(self) -> bool:
        return self.size < 0
    
    def is_flat(self) -> bool:
        return self.size == 0
    
    def __repr__(self):
        direction = "LONG" if self.is_long() else "SHORT" if self.is_short() else "FLAT"
        return f"Position({self.symbol}: {direction} {abs(self.size)} @ {self.avg_entry_price:.2f})"


class OrderManager:
    """Manages orders and positions."""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self._pending_orders: List[Order] = []
        
    def submit_order(self, order: Order) -> str:
        """Submit a new order."""
        self.orders[order.order_id] = order
        self._pending_orders.append(order)
        return order.order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.is_active():
                order.status = OrderStatus.CANCELLED
                return True
        return False
    
    def cancel_all(self, symbol: Optional[str] = None):
        """Cancel all orders, optionally filtered by symbol."""
        for order in self.orders.values():
            if order.is_active():
                if symbol is None or order.symbol == symbol:
                    order.status = OrderStatus.CANCELLED
    
    def get_position(self, symbol: str) -> Position:
        """Get or create position for symbol."""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        orders = [o for o in self.orders.values() if o.is_active()]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders
    
    def close_all_positions(self, timestamp: datetime, current_prices: Dict[str, float]) -> List[Order]:
        """Generate market orders to close all positions."""
        close_orders = []
        for symbol, position in self.positions.items():
            if not position.is_flat():
                side = OrderSide.SELL if position.is_long() else OrderSide.BUY
                order = Order(
                    symbol=symbol,
                    side=side,
                    size=-position.size,  # Opposite of current position
                    order_type=OrderType.MARKET,
                    timestamp=timestamp
                )
                close_orders.append(order)
        return close_orders
    
    def process_pending(self, timestamp: datetime, current_bar: Dict[str, 'pd.Series']) -> List[tuple]:
        """Process pending orders against current bar data.
        
        Returns list of (order, fill_price) tuples for filled orders.
        """
        fills = []
        still_pending = []
        
        for order in self._pending_orders:
            if order.symbol not in current_bar:
                still_pending.append(order)
                continue
            
            bar = current_bar[order.symbol]
            fill_price = None
            
            if order.order_type == OrderType.MARKET:
                # Market orders fill at open
                fill_price = bar['open']
            
            elif order.order_type == OrderType.LIMIT:
                # Limit order: buy below price, sell above price
                if order.is_buy() and bar['low'] <= order.price:
                    fill_price = min(order.price, bar['open']) if bar['open'] <= order.price else order.price
                elif order.is_sell() and bar['high'] >= order.price:
                    fill_price = max(order.price, bar['open']) if bar['open'] >= order.price else order.price
            
            elif order.order_type == OrderType.STOP:
                # Stop order: buy above price, sell below price
                if order.is_buy() and bar['high'] >= order.stop_price:
                    fill_price = max(order.stop_price, bar['open']) if bar['open'] >= order.stop_price else order.stop_price
                elif order.is_sell() and bar['low'] <= order.stop_price:
                    fill_price = min(order.stop_price, bar['open']) if bar['open'] <= order.stop_price else order.stop_price
            
            if fill_price is not None:
                order.fill_price = fill_price
                order.fill_time = timestamp
                order.status = OrderStatus.FILLED
                fills.append((order, fill_price))
            else:
                still_pending.append(order)
        
        self._pending_orders = still_pending
        return fills
