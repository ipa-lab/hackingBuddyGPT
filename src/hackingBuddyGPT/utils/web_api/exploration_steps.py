"""Named phases for the documentation endpoint-exploration state machine.

The exploration loop tracks progress with an integer ``current_step``. It used to
be compared against bare literals (``current_step == 2``) scattered across the
response handler and the documentation use-case. ``ExploreStep`` gives those
numbers names without changing any behaviour: it is an :class:`enum.IntEnum`, so
every existing integer comparison, ``+= 1`` increment and dict lookup keyed by
the step number keeps working exactly as before.

Steps 1-5 line up one-to-one with the structural endpoint buckets produced by
:mod:`hackingBuddyGPT.utils.web_api.endpoint_categorizer`.
"""
from enum import IntEnum


class ExploreStep(IntEnum):
    ROOT = 1          # e.g. /users
    INSTANCE = 2      # e.g. /users/{id}
    SUBRESOURCE = 3   # e.g. /users/profile
    RELATED = 4       # e.g. /users/{id}/posts
    MULTI_LEVEL = 5   # deeper / nested resources
    QUERY = 6         # query-parameter probing
    DONE = 7          # exploration finished
