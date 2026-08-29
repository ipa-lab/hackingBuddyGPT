from typing import Optional, override

from hackingBuddyGPT.capability import Capability


class TestCredentialCapability(Capability):
    """Shared base for the ``test_credential`` capabilities: the common tool name and the auth-error
    message helper. The actual login attempt and identity reporting differ per connector and stay in
    the subclass ``__call__`` / ``describe``.
    """

    @override
    def get_name(self) -> str:
        return "test_credential"

    @staticmethod
    def _auth_error(username: Optional[str] = None, password: Optional[str] = None) -> str:
        """The credential-failure message; names the credentials when both are supplied."""
        if username is not None and password is not None:
            return f"Authentication error, credentials {username}:{password} are wrong\n"
        return "Authentication error, credentials are wrong\n"
