import argparse
import sys

from hackingBuddyGPT.usecases.base import use_cases


def main():
    argss = sys.argv
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(required=True)
    for name, use_case in use_cases.items():
        if name.__contains__("API"):
            use_case.build_parser(subparser.add_parser(name=name, help=use_case.description))
            config_parser = subparser.add_parser(name="config", help="config file for execution")
            # Here you could add specific options for the 'config' command
            config_parser.add_argument('-c', '--config', required=True, help='Path to configuration file')
            config = config_parser.parse_args(argss[2:4])
            strategy_parser = subparser.add_parser(name="strategy", help="strategy for execution")
            # Here you could add specific options for the 'config' command
            strategy_parser.add_argument('-s', '--strategy', required=True, help='strategy')
            strategy = strategy_parser.parse_args(argss[4:])
        else:
            use_case.build_parser(subparser.add_parser(name=name, help=use_case.description))

    parsed = parser.parse_args(sys.argv[1:])
    configuration = {k: v for k, v in vars(parsed).items() if k not in ("use_case", "parser_state")}


    parsed = parser.parse_args(sys.argv[1:2])
    instance = parsed.use_case(parsed)
    instance.init(configuration=configuration)
    if instance.__class__.__name__.__contains__("API"):
        instance.agent.config_path = config.config
        instance.agent._strategy = strategy.strategy
    instance.init()

    instance.run()


if __name__ == "__main__":
    main()
