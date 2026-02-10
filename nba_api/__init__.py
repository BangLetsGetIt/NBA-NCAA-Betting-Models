"""
Local stub package for `nba_api` to prevent automated NBA API usage.

If `ALLOW_API_CALLS=1` is set in the environment this stub will delegate to
the real `nba_api` package (if installed). Otherwise, instantiating
endpoint classes will raise a clear error to prevent accidental calls.
"""
import os
import importlib

_ALLOW = os.getenv('ALLOW_API_CALLS') == '1'

if _ALLOW:
    # Delegate to installed package
    _real = importlib.import_module('nba_api')
    from nba_api import *  # type: ignore
else:
    # Minimal placeholders; real functionality is intentionally disabled
    __all__ = ['stats']
