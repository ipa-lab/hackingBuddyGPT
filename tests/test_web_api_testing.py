import argparse
import unittest
from hackingBuddyGPT.usecases.base import use_cases
from hackingBuddyGPT.usecases.web_api_testing.simple_web_api_testing import SimpleWebAPITestingUseCase
from hackingBuddyGPT.utils import DbStorage, Console



class WebAPITestingTestCase(unittest.TestCase):
    def test_simple_web_api_testing(self):

        log_db = DbStorage(':memory:')
        console = Console()

        log_db.init()
        parser = argparse.ArgumentParser()
        subparser = parser.add_subparsers(required=True)
        for name, use_case in use_cases.items():
            use_case.build_parser(subparser.add_parser(
                name=use_case.name,
                help=use_case.description
            ))

        parsed = parser.parse_args(["SimpleWebAPITesting"])
        instance = parsed.use_case(parsed)

        agent = instance.agent
        simple_web_api_testing = SimpleWebAPITestingUseCase(
            agent=agent,
            log_db=log_db,
            console=console,
            tag='web_api_testing',
            max_turns=20
        )

        simple_web_api_testing.init()
        result = simple_web_api_testing.run()
        # TODO: find condition for testing


if __name__ == '__main__':
    unittest.main()
