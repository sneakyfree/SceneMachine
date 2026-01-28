"""Re-export for backward compatibility.

Many tests import from scenemachine.api.main, so we provide a re-export here.
The actual app is in scenemachine.api.app.
"""

from scenemachine.api.app import app, create_app

__all__ = ["app", "create_app"]
