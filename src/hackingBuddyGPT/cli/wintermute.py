import argparse
import sys

from hackingBuddyGPT.usecases.usecase import use_cases
from hackingBuddyGPT.utils.configurable import CommandMap, InvalidCommand, Parseable, instantiate


def main():
    use_case_parsers: CommandMap = {
        name: Parseable(use_case, description=use_case.description)
        for name, use_case in use_cases.items()
    }
    try:
        instance, configuration = instantiate(sys.argv, use_case_parsers)
    except InvalidCommand as e:
        if len(f"{e}") > 0:
            print(e)
        print(e.usage)
        sys.exit(1)
    instance.run(configuration)


if __name__ == "__main__":
    main()
