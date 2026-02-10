"""
Stubs for common `nba_api.stats.endpoints` classes used by models.

Each endpoint class raises a RuntimeError when instantiated unless
`ALLOW_API_CALLS=1` is set in the environment. This prevents automated
network calls while making it obvious where to re-enable.
"""
import os
import importlib

_ALLOW = os.getenv('ALLOW_API_CALLS') == '1'

if _ALLOW:
    # Delegate to real endpoints
    _real = importlib.import_module('nba_api.stats.endpoints')
    LeagueDashPlayerStats = _real.LeagueDashPlayerStats
    LeagueDashTeamStats = _real.LeagueDashTeamStats
    PlayerGameLog = _real.PlayerGameLog
else:
    class _DisabledEndpoint:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "nba_api endpoint usage is disabled. Set ALLOW_API_CALLS=1 to enable external API calls."
            )

    class leaguedashplayerstats(_DisabledEndpoint):
        pass

    class leaguedashteamstats(_DisabledEndpoint):
        pass

    class playergamelog(_DisabledEndpoint):
        pass
