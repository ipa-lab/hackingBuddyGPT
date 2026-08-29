from typing import Dict

from hackingBuddyGPT.capability import Capability, CapabilityRegistry
from hackingBuddyGPT.utils.logging import Logger


class CapabilityManager(CapabilityRegistry):
    """Capability registry for the strategy-based use-cases (``CommandStrategy`` priv-esc, the
    ``SimpleStrategy`` web-api engines). All registration/lookup/execution logic lives in the shared
    :class:`~hackingBuddyGPT.capability.CapabilityRegistry` mixin; this only supplies per-instance
    storage and the ``log``.
    """

    log: Logger = None

    def __init__(self, log):
        self.log = log
        # Per-instance storage (not class-level) so separate managers don't share capabilities.
        self._capabilities: Dict[str, Capability] = {}
        self._default_capability: Capability = None

