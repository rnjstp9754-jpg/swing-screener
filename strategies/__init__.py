"""Strategy package"""
from .base_strategy import BaseStrategy
from .bollinger_rsi import BollingerRSIStrategy
# from .sepa_minervini import SEPAStrategy  # Classic SEPA - Closed
from .weinstein_stage import WeinsteinStrategy
from .k_sepa import KMinerviniProStrategy
from .aggressive_sepa import AggressiveSEPAStrategy

__all__ = ['BaseStrategy', 'BollingerRSIStrategy', 'WeinsteinStrategy', 'KMinerviniProStrategy', 'AggressiveSEPAStrategy']
