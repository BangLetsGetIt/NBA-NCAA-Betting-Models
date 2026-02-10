"""
Stub for `nba_api.stats` subpackage.

Defines a small safe surface and intentionally disables endpoint usage
unless `ALLOW_API_CALLS=1` is set.
"""
import os
import importlib

_ALLOW = os.getenv('ALLOW_API_CALLS') == '1'

if _ALLOW:
    # Delegate to installed package
    _real_stats = importlib.import_module('nba_api.stats')
    from nba_api.stats import *  # type: ignore
else:
    __all__ = ['endpoints', 'static']
