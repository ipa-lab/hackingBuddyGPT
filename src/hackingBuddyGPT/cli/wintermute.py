import asyncio
import argparse
import sys

from hackingBuddyGPT.usecases.base import use_cases


async def run_instance(instance, configuration):
    await instance.init(configuration=configuration)
    await instance.run()



def main():
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(required=True)
    for name, use_case in use_cases.items():
        use_case.build_parser(subparser.add_parser(name=name, help=use_case.description))

    parsed = parser.parse_args(sys.argv[1:])
    configuration = {k: v for k, v in vars(parsed).items() if k not in ("use_case", "parser_state")}
    if "llm.api_key" in configuration: # do not leak the API key
        del configuration["llm.api_key"]
    instance = parsed.use_case(parsed)
    asyncio.run(run_instance(instance, configuration))


if __name__ == "__main__":
    main()
