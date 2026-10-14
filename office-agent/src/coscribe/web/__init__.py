"""Local Web UI: a FastAPI process serving the chat WebSocket protocol and
the static frontend, bridging Runner's synchronous tool-approval callback
to a WebSocket wait (see session.py's ChatSession)."""

# The package re-exports nothing: the entry points are `app.create_app_lg` and `app.main`
# (the `coscribe-web` script), and the module card lists them.
__all__: list[str] = []
