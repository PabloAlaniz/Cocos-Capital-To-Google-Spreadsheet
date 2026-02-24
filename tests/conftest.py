"""Pytest configuration and fixtures."""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock config module before any imports
class MockConfig:
    GMAIL_USER = 'test@example.com'
    GMAIL_APP_PASS = 'test_password'
    prefix_buy = 'BUY_'
    prefix_sell = 'SELL_'
    config = {}

sys.modules['config'] = MockConfig()
