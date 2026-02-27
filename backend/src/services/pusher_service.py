import os
import pusher


class PusherService:
    """Thin wrapper around the Pusher HTTP client, pointed at a self-hosted Soketi instance."""

    def __init__(self):
        self.client = pusher.Pusher(
            app_id=os.environ.get("SOKETI_APP_ID", "1"),
            key=os.environ.get("SOKETI_APP_KEY", "eye-budget-key"),
            secret=os.environ.get("SOKETI_APP_SECRET", "eye-budget-secret"),
            host=os.environ.get("SOKETI_HOST", "localhost"),
            port=int(os.environ.get("SOKETI_PORT", "6001")),
            ssl=False,
        )

    def trigger(self, channel: str, event: str, data: dict) -> None:
        """Push an event to the given channel. Failures are logged but never re-raised."""
        try:
            self.client.trigger(channel, event, data)
        except Exception as exc:
            print(f"[pusher] Failed to trigger '{event}' on '{channel}': {exc}")
