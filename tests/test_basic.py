"""
Basic tests for futures backtesting framework.
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime

import sys
sys.path.insert(0, '..')

from futures_backtesting import (
    get_contract, calculate_pnl,
    get_prop_firm, DrawdownType,
    DataFeed, MultiDataFeed,
    Order, OrderType, OrderSide
)


class TestContracts(unittest.TestCase):
    def test_mes_contract(self):
        contract = get_contract('MES')
        self.assertEqual(contract.symbol, 'MES')
        self.assertEqual(contract.tick_value, 1.25)
        self.assertEqual(contract.point_value, 5.0)
    
    def test_mnq_contract(self):
        contract = get_contract('MNQ')
        self.assertEqual(contract.symbol, 'MNQ')
        self.assertEqual(contract.tick_value, 0.50)
    
    def test_pnl_calculation(self):
        # MES: 2 ticks = 2 * 1.25 = 2.50
        pnl = calculate_pnl('MES', 4500.00, 4500.50, 1)
        self.assertEqual(pnl, 2.50)
        
        # MNQ: 4 ticks = 4 * 0.50 = 2.00
        pnl = calculate_pnl('MNQ', 15000.00, 15001.00, 1)
        self.assertEqual(pnl, 2.00)


class TestPropFirms(unittest.TestCase):
    def test_topstep_config(self):
        config = get_prop_firm('topstep_50k')
        self.assertEqual(config.initial_balance, 50000)
        self.assertEqual(config.position_close_time, '16:00')
        self.assertEqual(config.drawdown_type, DrawdownType.EOD_TRAILING)
    
    def test_lucid_config(self):
        config = get_prop_firm('lucid_50k')
        self.assertEqual(config.position_close_time, '17:00')
        self.assertEqual(config.drawdown_type, DrawdownType.INTRADAY_TRAILING)


class TestDataFeed(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [99, 100, 101],
            'close': [103, 104, 105],
            'volume': [1000, 1100, 1200]
        }, index=pd.date_range('2024-01-01', periods=3, freq='5min'))
    
    def test_data_feed_creation(self):
        feed = DataFeed(self.data, 'TEST')
        self.assertEqual(len(feed), 3)
        self.assertEqual(feed.symbol, 'TEST')


class TestOrders(unittest.TestCase):
    def test_market_order(self):
        order = Order(
            symbol='MES',
            side=OrderSide.BUY,
            size=2,
            order_type=OrderType.MARKET
        )
        self.assertTrue(order.is_buy())
        self.assertFalse(order.is_sell())
    
    def test_limit_order(self):
        order = Order(
            symbol='MES',
            side=OrderSide.SELL,
            size=1,
            order_type=OrderType.LIMIT,
            price=4500
        )
        self.assertEqual(order.price, 4500)


if __name__ == '__main__':
    unittest.main()
