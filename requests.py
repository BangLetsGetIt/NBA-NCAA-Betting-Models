"""
Local shim for `requests` to prevent automated HTTP calls.

By default this module raises on network calls. To allow real network
requests for a controlled run set environment variable `ALLOW_API_CALLS=1`.

This file intentionally shadows the external `requests` package when
running scripts from the repo root, preventing accidental automated API
calls from model code that does `import requests`.
"""
import os
import importlib
from types import SimpleNamespace

_ALLOW = os.getenv('ALLOW_API_CALLS') == '1'

if _ALLOW:
    # Delegate to the real requests package
    _real = importlib.import_module('requests')
    get = _real.get
    post = _real.post
    put = _real.put
    Session = _real.Session
    exceptions = _real.exceptions
    RequestException = _real.RequestException
else:
    def _blocked(*args, **kwargs):
        raise RuntimeError(
            "Automated network requests are disabled. Set ALLOW_API_CALLS=1 to enable."
        )

    class _BlockedSession:
        def request(self, *args, **kwargs):
            return _blocked()

        def get(self, *args, **kwargs):
            return _blocked()

        def post(self, *args, **kwargs):
            return _blocked()

    # Export the common API surface used across the repo
    get = _blocked
    post = _blocked
    put = _blocked
    Session = _BlockedSession
    exceptions = SimpleNamespace()
    RequestException = RuntimeError

def __getattr__(name):
    # Defensive: any other attribute access should either be delegated or blocked
    if _ALLOW:
        return getattr(_real, name)
    raise RuntimeError(
        f"Access to 'requests.{name}' is blocked. Set ALLOW_API_CALLS=1 to enable network calls."
    )
