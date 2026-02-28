import os
import pusher


class PusherService:
    """Thin wrapper around the Pusher HTTP client, pointed at a self-hosted Soketi instance."""

    def __init__(self):
        app_id = (os.environ.get("SOKETI_APP_ID") or "1").strip()
        key = (os.environ.get("SOKETI_APP_KEY") or "eye-budget-key").strip()
        secret = (os.environ.get("SOKETI_APP_SECRET") or "eye-budget-secret").strip()
        host = (os.environ.get("SOKETI_HOST") or "localhost").strip()
        port = int((os.environ.get("SOKETI_PORT") or "6001").strip())
        try:
            self.client = pusher.Pusher(
                app_id=app_id,
                key=key,
                secret=secret,
                host=host,
                port=port,
                ssl=False,
            )
        except Exception as exc:
            print(f"[pusher] Failed to initialize Pusher client (app_id={app_id!r}, host={host!r}, port={port!r}): {exc}")
            self.client = None

    def trigger(self, channel: str, event: str, data: dict) -> None:
        """Push an event to the given channel. Failures are logged but never re-raised."""
        if self.client is None:
            print(f"[pusher] Client not initialized, skipping trigger '{event}' on '{channel}'")
            return
        try:
            self.client.trigger(channel, event, data)
        except Exception as exc:
            print(f"[pusher] Failed to trigger '{event}' on '{channel}': {exc}")
