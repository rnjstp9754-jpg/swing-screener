"""Strategy package"""
from .base_strategy import BaseStrategy
from .bollinger_rsi import BollingerRSIStrategy

__all__ = ['BaseStrategy', 'BollingerRSIStrategy']
