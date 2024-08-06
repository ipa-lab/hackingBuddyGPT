import argparse
import sys

from hackingBuddyGPT.usecases.base import use_cases


def main():
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(required=True)
    for name, use_case in use_cases.items():
        use_case.build_parser(subparser.add_parser(
            name=use_case.name,
            help=use_case.description
        ))

    parsed = parser.parse_args(sys.argv[1:])
    configuration = {k: v for k, v in vars(parsed).items() if k not in ("use_case", "parser_state")}
    instance = parsed.use_case(parsed)
    instance.init(configuration=configuration)
    instance.run()


if __name__ == "__main__":
    main()
