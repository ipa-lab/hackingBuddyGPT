"""Characterisation (golden) tests for the pentesting prompt engine.

These pin the *exact* generated pentesting prompt for each strategy so a
behaviour-preserving refactor of the prompt classes (deduplicating
``_get_pentesting_steps`` / ``transform_into_prompt_structure``) can prove it did not
change the output. Randomness is made deterministic by seeding Faker + ``random``.

The golden md5s are tied to this seed and the installed Faker version; if a Faker
upgrade changes seed(0) output, regenerate them (the structural substring assertions
below stay valid regardless).
"""
import hashlib
import json
import os
import random
import unittest

from faker import Faker

from hackingBuddyGPT.utils.openapi.openapi_parser import OpenAPISpecificationParser
from hackingBuddyGPT.utils.prompt_generation.prompt_generation_helper import PromptGenerationHelper
from hackingBuddyGPT.utils.prompt_generation.information import (
    PenTestingInformation,
    PromptContext,
    PromptPurpose,
    strategy_from_string,
)
from hackingBuddyGPT.utils.prompt_generation.prompt_engineer import PromptEngineer

CONFIG = os.path.join(os.path.dirname(__file__), "test_files", "fakeapi_config.json")

GOLDEN_MD5 = {
    "icl": "a5f1b063e4f873fa7c5edfb2167d0944",
    "cot": "a4e4fc0e8f9f9f9774bbf7f1ef07988a",
    "tot": "fd9862563d25406e6627ef77ca2cf7ef",
}


class TestPentestingPromptCharacterization(unittest.TestCase):
    def _generate(self, strategy: str) -> str:
        # Seed BEFORE constructing anything faker/random-dependent so output is reproducible.
        Faker.seed(0)
        random.seed(0)
        parser = OpenAPISpecificationParser(CONFIG)
        with open(CONFIG) as f:
            config = json.load(f)
        helper = PromptGenerationHelper(config.get("host"), config.get("description"))
        pentesting_information = PenTestingInformation(parser, config)
        pentesting_information.pentesting_step_list = [PromptPurpose.SETUP, PromptPurpose.VERIY_SETUP]
        engineer = PromptEngineer(
            strategy=strategy_from_string(strategy),
            prompt_helper=helper,
            context=PromptContext.PENTESTING,
            open_api_spec=parser.api_data,
            rest_api_info=(config.get("token"), config.get("description"),
                           config.get("correct_endpoints", {}), parser.classify_endpoints()),
        )
        engineer.set_pentesting_information(pentesting_information=pentesting_information)
        return engineer.generate_prompt(hint="", turn=1)[0].get("content")

    def _assert_golden(self, strategy, *, anchor):
        prompt = self._generate(strategy)
        self.assertIn(anchor, prompt)
        self.assertEqual(
            hashlib.md5(prompt.encode()).hexdigest(),
            GOLDEN_MD5[strategy],
            f"generated {strategy} pentesting prompt changed:\n{prompt!r}",
        )

    def test_icl_pentesting_prompt_unchanged(self):
        self._assert_golden("icl", anchor="Phase: Setup tests")

    def test_cot_pentesting_prompt_unchanged(self):
        self._assert_golden("cot", anchor="Let's think step by step.")

    def test_tot_pentesting_prompt_unchanged(self):
        self._assert_golden("tot", anchor="Root Objective: Objective: Setup tests")


if __name__ == "__main__":
    unittest.main()
