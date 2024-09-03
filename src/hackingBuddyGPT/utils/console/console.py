from rich import console

from hackingBuddyGPT.utils.configurable import configurable


@configurable("console", "Console")
class Console(console.Console):
    """
    Simple wrapper around the rich Console class, to allow for dependency injection and configuration.
    """

    def __init__(self):
        super().__init__()
