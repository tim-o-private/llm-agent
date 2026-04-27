"""Custom exceptions for the chat server."""


class ReauthRequiredError(Exception):
    """Raised when a user's OAuth token has expired or been revoked and re-authentication is required."""

    def __init__(self, service_name: str, message: str | None = None):
        self.service_name = service_name
        if message is None:
            message = (
                f"Please reconnect your {service_name} account in Settings > Integrations."
            )
        super().__init__(message)
