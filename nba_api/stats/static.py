"""
Stub for `nba_api.stats.static` used by models (players lookup).

If API calls are disabled this provides a minimal `players` object with
`get_players()` that returns an empty list. When `ALLOW_API_CALLS=1` is
set the module delegates to the installed `nba_api` package.
"""
import os
import importlib

_ALLOW = os.getenv('ALLOW_API_CALLS') == '1'

if _ALLOW:
    _real = importlib.import_module('nba_api.stats.static')
    from nba_api.stats.static import *  # type: ignore
else:
    class _PlayersStub:
        @staticmethod
        def get_players():
            return []

    players = _PlayersStub()
