import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import override

from hackingBuddyGPT.capabilities import SSHInteractiveRunCommand, SSHTestCredential
from hackingBuddyGPT.utils.shell_root_detection import (
    LOGIN_AS_ROOT_SUCCESSFUL,
    ROOT_PROOF_ENV,
    new_root_proof_challenge,
    redact_root_proof,
    root_proof_challenge_matches,
)


@dataclass
class LinuxPrivEscRunCommand(SSHInteractiveRunCommand):
    """Run a command and verify root in the same persistent shell."""

    on_root: Callable[[], None] | None = None
    root_verified: bool = field(default=False, init=False)
    _root_proof: str = field(default_factory=lambda: os.environ.get(ROOT_PROOF_ENV, ""), init=False, repr=False)
    _verification_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    @override
    async def __call__(self, command: str) -> str:
        async with self._verification_lock:
            self.root_verified = False
            output = await super().__call__(command)
            uid_before = self.conn.last_uid

            if uid_before == 0 and self._root_proof:
                challenge, digest = new_root_proof_challenge(self._root_proof)
                challenge_output = await super().__call__(challenge)
                self.root_verified = self.conn.last_uid == 0 and root_proof_challenge_matches(challenge_output, digest)

            if self.root_verified and self.on_root is not None:
                self.on_root()
            return redact_root_proof(output, self._root_proof)


@dataclass
class LinuxPrivEscTestCredential(SSHTestCredential):
    """Verify root through a fresh SSH login."""

    on_root: Callable[[], None] | None = None
    root_verified: bool = field(default=False, init=False)

    @override
    async def __call__(self, username: str, password: str) -> str:
        self.root_verified = False
        result = await super().__call__(username, password)
        self.root_verified = result == LOGIN_AS_ROOT_SUCCESSFUL
        if self.root_verified and self.on_root is not None:
            self.on_root()
        return result
