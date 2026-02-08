"""
Micro futures contract specifications.
"""
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ContractSpec:
    """Futures contract specification."""
    symbol: str
    name: str
    tick_size: float
    tick_value: float  # $ per tick
    point_value: float  # $ per full point
    margin_day: float  # Intraday margin estimate
    margin_overnight: float  # Overnight margin estimate
    trading_hours: tuple  # (start_time, end_time) in ET
    close_time: str  # Time when daily session ends
    
    def __repr__(self):
        return f"{self.symbol} ({self.name})"


# Micro E-mini S&P 500
MES = ContractSpec(
    symbol="MES",
    name="Micro E-mini S&P 500",
    tick_size=0.25,
    tick_value=1.25,
    point_value=5.0,
    margin_day=200.0,
    margin_overnight=1100.0,
    trading_hours=("18:00", "17:00"),  # Sun-Fri 6PM-5PM next day ET
    close_time="17:00"
)

# Micro E-mini Nasdaq-100
MNQ = ContractSpec(
    symbol="MNQ",
    name="Micro E-mini Nasdaq-100",
    tick_size=0.25,
    tick_value=0.50,
    point_value=2.0,
    margin_day=100.0,
    margin_overnight=660.0,
    trading_hours=("18:00", "17:00"),
    close_time="17:00"
)

# Micro Gold
MGC = ContractSpec(
    symbol="MGC",
    name="Micro Gold",
    tick_size=0.10,
    tick_value=1.00,
    point_value=10.0,
    margin_day=250.0,
    margin_overnight=1100.0,
    trading_hours=("18:00", "17:00"),
    close_time="17:00"
)

# Micro E-mini Dow
MYM = ContractSpec(
    symbol="MYM",
    name="Micro E-mini Dow",
    tick_size=1.00,
    tick_value=0.50,
    point_value=0.50,
    margin_day=100.0,
    margin_overnight=880.0,
    trading_hours=("18:00", "17:00"),
    close_time="17:00"
)

# Contract registry
CONTRACTS: Dict[str, ContractSpec] = {
    "MES": MES,
    "MNQ": MNQ,
    "MGC": MGC,
    "MYM": MYM,
}


def get_contract(symbol: str) -> ContractSpec:
    """Get contract specification by symbol."""
    symbol = symbol.upper()
    if symbol not in CONTRACTS:
        raise ValueError(f"Unknown contract symbol: {symbol}. Available: {list(CONTRACTS.keys())}")
    return CONTRACTS[symbol]


def calculate_pnl(symbol: str, entry_price: float, exit_price: float, contracts: int = 1) -> float:
    """Calculate P&L for a trade.
    
    Args:
        symbol: Contract symbol
        entry_price: Entry price
        exit_price: Exit price
        contracts: Number of contracts (positive for long, negative for short)
        
    Returns:
        Profit/loss in dollars
    """
    contract = get_contract(symbol)
    price_diff = exit_price - entry_price
    points = price_diff / contract.tick_size
    ticks = points
    pnl = ticks * contract.tick_value * contracts
    return pnl
