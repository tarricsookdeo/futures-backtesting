"""
Risk management for prop firm trading.
"""
from typing import Optional, Dict
from datetime import datetime, time
import pandas as pd

from ..prop_firms.configs import PropFirmConfig, DrawdownType


class RiskManager:
    """Manages prop firm risk rules."""
    
    def __init__(self, config: PropFirmConfig):
        self.config = config
        self._daily_pnl: Dict[datetime, float] = {}
        self._current_day: Optional[datetime] = None
        self._day_start_equity: float = config.initial_balance
        self._equity_high: float = config.initial_balance
        self._intraday_high: float = config.initial_balance
        self._daily_loss_limit_hit: bool = False
        self._max_loss_hit: bool = False
        
    def update(self, timestamp: datetime, equity: float) -> Dict[str, any]:
        """
        Update risk status with current equity.
        
        Returns dict with:
        - can_trade: bool
        - close_positions: bool
        - violation: Optional[str]
        """
        # Detect new trading day
        current_day = timestamp.date()
        if self._current_day != current_day:
            self._current_day = current_day
            self._day_start_equity = equity
            self._intraday_high = equity
            self._daily_loss_limit_hit = False
        
        # Update highs
        if equity > self._intraday_high:
            self._intraday_high = equity
        if equity > self._equity_high:
            self._equity_high = equity
        
        # Check time-based close
        current_time = timestamp.time()
        close_time = self._parse_time(self.config.position_close_time)
        
        if current_time >= close_time:
            return {
                'can_trade': False,
                'close_positions': True,
                'violation': f"Close time reached ({self.config.position_close_time} ET)"
            }
        
        # Check daily loss limit
        daily_pnl = equity - self._day_start_equity
        if daily_pnl <= -self.config.max_daily_loss:
            self._daily_loss_limit_hit = True
            return {
                'can_trade': False,
                'close_positions': True,
                'violation': f"Daily loss limit hit: ${-daily_pnl:.2f}"
            }
        
        # Check max loss / drawdown
        drawdown = self._calculate_drawdown(equity)
        if drawdown >= self.config.max_loss:
            self._max_loss_hit = True
            return {
                'can_trade': False,
                'close_positions': True,
                'violation': f"Max loss hit: ${drawdown:.2f}"
            }
        
        return {
            'can_trade': True,
            'close_positions': False,
            'violation': None
        }
    
    def _calculate_drawdown(self, equity: float) -> float:
        """Calculate current drawdown based on firm type."""
        if self.config.drawdown_type == DrawdownType.STATIC:
            # Static drawdown from starting balance
            return self.config.drawdown_start_value - equity
        
        elif self.config.drawdown_type == DrawdownType.EOD_TRAILING:
            # End-of-day trailing: trails from high water mark at close
            return self._equity_high - equity
        
        elif self.config.drawdown_type == DrawdownType.INTRADAY_TRAILING:
            # Intraday trailing: trails from intraday high
            return self._intraday_high - equity
        
        return 0.0
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string to time object."""
        if ':' in time_str:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        return time(int(time_str), 0)
    
    def can_open_position(self, symbol: str, size: int, current_positions: Dict) -> tuple:
        """Check if a new position can be opened."""
        # Check max contracts
        if self.config.max_contracts:
            current_size = sum(abs(p.size) for p in current_positions.values())
            if current_size + abs(size) > self.config.max_contracts:
                return False, f"Max contracts exceeded ({self.config.max_contracts})"
        
        # Check if we're allowed to trade
        if self._daily_loss_limit_hit:
            return False, "Daily loss limit hit"
        if self._max_loss_hit:
            return False, "Max loss hit"
        
        return True, None
    
    def get_status(self) -> Dict:
        """Get current risk status."""
        return {
            'initial_balance': self.config.initial_balance,
            'day_start_equity': self._day_start_equity,
            'equity_high': self._equity_high,
            'intraday_high': self._intraday_high,
            'max_loss': self.config.max_loss,
            'drawdown_type': self.config.drawdown_type.value,
            'daily_loss_limit_hit': self._daily_loss_limit_hit,
            'max_loss_hit': self._max_loss_hit,
        }
