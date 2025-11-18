import asyncio
import sys

from hackingBuddyGPT.usecases.base import use_cases
from hackingBuddyGPT.utils.configurable import CommandMap, InvalidCommand, Parseable, instantiate


def main():
    use_case_parsers: CommandMap[...] = {
        name: Parseable(use_case, description=use_case.description) for name, use_case in use_cases.items()
    }
    try:
        instance, configuration = instantiate(sys.argv, use_case_parsers)
    except InvalidCommand as e:
        if len(f"{e}") > 0:
            print(e)
        print(e.usage)
        sys.exit(1)
    try:
        asyncio.run(instance.run(configuration))
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(1)
    except Exception:
        # there is something that is blocking on exit and I don't have the time to figure out what it is
        # I already spent 1.5h...
        import traceback

        traceback.print_exc()

        import os

        os._exit(1)


if __name__ == "__main__":
    main()
