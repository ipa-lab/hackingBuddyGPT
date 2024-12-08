from typing import Optional, List, Dict

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.task_planning import (
    TaskPlanningPrompt,
)
from hackingBuddyGPT.usecases.web_api_testing.utils.custom_datatypes import Prompt


class TreeOfThoughtPrompt(TaskPlanningPrompt):
    """
    A class that generates prompts using the tree-of-thought strategy.

    This class extends the BasicPrompt abstract base class and implements
    the generate_prompt method for creating prompts based on the
    tree-of-thought strategy.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        rest_api (str): The REST API endpoint for which prompts are generated.
        round (int): The round number for the prompt generation process.
        purpose (Optional[PromptPurpose]): The purpose of the prompt generation, which can be set during the process.
    """

    def __init__(self, context: PromptContext, prompt_helper) -> None:
        """
        Initializes the TreeOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            round (int): The round number for the prompt generation process.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.TREE_OF_THOUGHT)

    def generate_prompt(self, move_type: str, hint: Optional[str], previous_prompt: Prompt, turn: Optional[int]) -> str:
        """
        Generates a prompt using the tree-of-thought strategy.

        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (List[Union[ChatCompletionMessage, ChatCompletionMessageParam]]): A list of previous prompt entries, each containing a "content" key.
            turn (Optional[int]): The current turn or step in the conversation.

        Returns:
            str: The generated prompt.
        """
        common_steps = self._get_common_steps()
        if self.context == PromptContext.DOCUMENTATION:
            self.purpose = PromptPurpose.DOCUMENTATION
            chain_of_thought_steps = self._get_documentation_steps(common_steps, move_type)
        else:
            chain_of_thought_steps = self._get_pentesting_steps(move_type)
        if hint:
            chain_of_thought_steps.append(hint)

        return self.prompt_helper.check_prompt(previous_prompt=previous_prompt, steps=chain_of_thought_steps)

    def _get_pentesting_steps(self, move_type: str, common_step: Optional[str] = "") -> Any:
        """
        Provides the steps for the Tree-of-Thought strategy in the pentesting context.

        Args:
            move_type (str): The type of move to generate, e.g., "explore".
            common_step (Optional[str]): A list of common steps for generating prompts.

        Returns:
            List[str]: A list of steps for the Tree-of-Thought strategy in the pentesting context.
        """
        if self.pentest_steps is None:
            self.pentest_steps = self.pentesting_information.explore_steps()

        purpose = self.purpose
        test_cases = self.pentesting_information.get_steps_of_phase(purpose, self.pentest_steps)

        if move_type == "explore":
            # Check if the purpose has already been transformed into Tree-of-Thought structure
            if purpose not in self.transformed_steps.keys():
                for test_case in test_cases:
                    if purpose not in self.transformed_steps.keys():
                        self.transformed_steps[purpose] = []
                    # Transform test cases into Tree-of-Thought structure based on purpose
                    self.transformed_steps[purpose].append(
                        self.transform_to_tree_of_thought(test_case, purpose)
                    )

            # Extract the ToT structure for the current purpose
            tot_steps = self.transformed_steps[purpose]

            # Process steps branch by branch, with memory of explored steps and conditional handling
            for step in tot_steps:
                if step not in self.explored_steps:
                    self.explored_steps.append(step)
                    print(f"Processing Branch: {step}")
                    self.current_step = step
                    # Process the step and return its formatted representation
                    formatted_step = self.transform_tree_of_thought_to_string(step, "steps")
                    last_item = tot_steps[-1]

                    if step == last_item:
                        # If it's the last step, remove the purpose and update self.purpose
                        if purpose in self.pentesting_information.pentesting_step_list:
                            self.pentesting_information.pentesting_step_list.remove(purpose)
                        if self.pentesting_information.pentesting_step_list:
                            self.purpose = self.pentesting_information.pentesting_step_list[0]

                    return [formatted_step]

        else:
            return ["Look for exploits."]

    def transform_to_tree_of_thought(self, test_case, purpose):
        """
        Transforms a single test case into a Tree-of-Thought structure.

        The transformation incorporates branching reasoning paths, self-evaluation at decision points,
        and backtracking to enable deliberate problem-solving.

        Args:
            test_case (dict): A dictionary representing a single test case with fields like 'objective', 'steps',
                              'security', and 'expected_response_code'.
            purpose (str): The overarching purpose of the test case.

        Returns:
            dict: A transformed test case structured as a Tree-of-Thought process.
        """

        # Initialize the root of the tree
        transformed_case = {
            "root": f"Objective: {test_case['objective']}",
            "branches": [],
            "assessments": []
        }

        # Process steps in the test case as potential branches
        for i, step in enumerate(test_case["steps"]):
            # Handle security and expected response codes conditionally
            security = (
                test_case["security"][i]
                if len(test_case["security"]) > 1
                else test_case["security"][0]
            )
            expected_response_code = (
                test_case["expected_response_code"][i]
                if isinstance(test_case["expected_response_code"], list) and len(
                    test_case["expected_response_code"]) > 1
                else test_case["expected_response_code"]
            )

            # Define a branch representing a single reasoning path
            branch = {
                "step": step,
                "security": security,
                "expected_response_code": expected_response_code,
                "thoughts": [
                    {
                        "action": f"Execute: {step}",
                        "conditions": {
                            "if_successful": {
                                "outcome": "No Vulnerability found.",
                                "next_action": "Proceed to the next step."
                            },
                            "if_unsuccessful": {
                                "outcome": "Vulnerability found.",
                                "next_action": "Reevaluate this step or explore alternative actions."
                            }
                        }
                    }
                ]
            }
            # Add branch to the tree
            transformed_case["branches"].append(branch)

        # Add an assessment mechanism for self-evaluation
        transformed_case["assessments"].append(
            {
                "phase_review": "Review outcomes of all branches. If any branch fails to meet objectives, backtrack and revise steps."
            }
        )

        # Add a final assessment for the entire tree
        transformed_case["final_assessment"] = {
            "criteria": "Confirm all objectives are met across all branches.",
            "next_action": "If objectives are not met, revisit unresolved branches."
        }

        return transformed_case


    def transform_tree_of_thought_to_string(self, tree_of_thought, character):
        """
        Transforms a Tree-of-Thought structured test case into a formatted string representation.

        Args:
            tree_of_thought (dict): The output from the `transform_to_tree_of_thought` function, representing
                                    a tree-structured test case.
            character (str): The focus of the transformation, which could be 'steps', 'assessments', or 'final_assessment'.

        Returns:
            str: A formatted string representation of the Tree-of-Thought structure.
        """
        # Initialize the result string
        result = []

        # Add the root objective
        result.append(f"Root Objective: {tree_of_thought['root']}\n\n")

        # Handle branches
        if character == "steps":
            result.append("Branches (Step-by-Step Thinking):\n")
            for idx, branch in enumerate(tree_of_thought["branches"], start=1):
                result.append(f"  Branch {idx}:\n")
                result.append(f"    Step: {branch['step']}\n")
                result.append(f"    Security: {branch['security']}\n")
                result.append(f"    Expected Response Code: {branch['expected_response_code']}\n")
                result.append("    Thoughts:\n")
                for thought in branch["thoughts"]:
                    result.append(f"      Action: {thought['action']}\n")
                    result.append("      Conditions:\n")
                    for condition, outcome in thought["conditions"].items():
                        result.append(f"        {condition.capitalize()}: {outcome['outcome']}\n")
                        result.append(f"          Next Action: {outcome['next_action']}\n")
                result.append("\n")

        # Handle assessments
        if character == "assessments":
            result.append("\nAssessments:\n")
            for assessment in tree_of_thought["assessments"]:
                result.append(f"  - {assessment['phase_review']}\n")

        # Handle final assessment
        if character == "final_assessment":
            if "final_assessment" in tree_of_thought:
                final_assessment = tree_of_thought["final_assessment"]
                result.append(f"\nFinal Assessment:\n")
                result.append(f"  Criteria: {final_assessment['criteria']}\n")
                result.append(f"  Next Action: {final_assessment['next_action']}\n")

        return ''.join(result)

    def transform_to_tree_of_thoughtx(self, prompts: Dict[str, List[List[str]]]) -> Dict[str, List[str]]:
        """
        Transforms prompts into a "Tree of Thought" (ToT) format with branching paths, checkpoints,
        and conditional steps for flexible, iterative problem-solving as per Tree of Thoughts methodology.
        Explanation and Justification

        This implementation aligns closely with the Tree of Thought (ToT) principles outlined by Xie et al. (2023):

        Iterative Evaluation: Each step incorporates assessment points to check if the outcome meets expectations, partially succeeds, or fails, facilitating iterative refinement.

        Dynamic Branching: Conditional branches allow for the creation of alternative paths ("sub-branches") based on intermediate outcomes. This enables the prompt to pivot when initial strategies don’t fully succeed.

        Decision Nodes: Decision nodes evaluate whether to proceed, retry, or backtrack, supporting a flexible problem-solving strategy. This approach mirrors the tree-based structure proposed in ToT, where decisions at each node guide the overall trajectory.

        Progress Checkpoints: Regular checkpoints ensure that each level’s insights are documented and assessed for readiness to proceed. This helps manage complex tasks by breaking down the process into comprehensible phases, similar to how ToT manages complexity in problem-solving.

        Hierarchical Structure: Each level in the hierarchy deepens the model's understanding, allowing for more detailed exploration at higher levels, a core concept in ToT’s approach to handling multi-step tasks.

        Args:
            prompts (Dict[str, List[List[str]]]): Dictionary of initial steps for various purposes.

        Returns:
            Dict[str, List[str]]: A dictionary where each purpose maps to a structured list of transformed steps in the ToT format.
        """
        tot_prompts = {}

        for purpose, steps_list in prompts.items():
            tree_steps = []
            current_level = 1

            for steps in steps_list:
                # Iterate through each step in the current level of the tree
                for step in steps:
                    # Main step execution path
                    tree_steps.append(f"Level {current_level} - Main Step: {step}")
                    tree_steps.append("  - Document initial observations.")
                    tree_steps.append("  - Assess: Is the goal partially or fully achieved?")

                    # Conditional branching for flexible responses
                    tree_steps.append("    - If fully achieved, proceed to the next main step.")
                    tree_steps.append(
                        "    - If partially achieved, identify areas that need refinement and retry with adjusted parameters.")
                    tree_steps.append("    - If unsuccessful, branch out to explore alternative strategies.")

                    # Add sub-branch for alternative exploration
                    tree_steps.append(
                        f"Sub-Branch at Level {current_level}: Retry with alternative strategy for Step: {step}")
                    tree_steps.append("  - Note adjustments and compare outcomes with previous attempts.")
                    tree_steps.append("  - If successful, integrate findings back into the main path.")

                    # Decision node for evaluating continuation or backtracking
                    tree_steps.append("Decision Node:")
                    tree_steps.append("  - Assess: Should we continue on this path, backtrack, or end this branch?")
                    tree_steps.append("  - If major issues persist, consider redefining prerequisites or conditions.")

                    # Checkpoint for overall progress assessment at each level
                    tree_steps.append(
                        f"Progress Checkpoint at Level {current_level}: Review progress, document insights, and confirm readiness to advance.")

                    # Increment to deeper level in the hierarchy for next step
                    current_level += 1

                # Conclude steps for this level, reset for new purpose-specific path
                tree_steps.append(
                    f"End of Level {current_level - 1}: Consolidate all insights before moving to the next logical phase.")
                current_level = 1  # Reset level for subsequent purposes

            # Add the structured Tree of Thought with branches and checkpoints to the final prompts dictionary
            tot_prompts[purpose] = tree_steps

        return tot_prompts


    def generate_documentation_steps(self, steps):
       return [ steps[0],
            [
                "Start by querying root-level resource endpoints.",
                "Focus on sending GET requests only to those endpoints that consist of a single path component directly following the root.",
                "For instance, paths should look like '/users' or '/products', with each representing a distinct resource type.",
                "Ensure to explore new paths that haven't been previously tested to maximize coverage."
            ],
            [
                "Next, move to instance-level resource endpoints.",
                "Identify and list endpoints formatted as `/resource/id`, where 'id' represents a dynamic parameter.",
                "Attempt to query these endpoints to validate whether the 'id' parameter correctly retrieves individual resource instances.",
                "Consider testing with various ID formats, such as integers, longs, or base62 encodings like '6rqhFgbbKwnb9MLmUQDhG6'."
            ],
            [
                "Proceed to analyze related resource endpoints.",
                "Identify patterns where a resource is associated with another through an 'id', formatted as `/resource/id/other_resource`.",
                "Start by cataloging endpoints that fit this pattern, particularly noting the position of 'id' between two resource identifiers.",
                "Then, methodically test these endpoints, using appropriate 'id' values, to explore their responses and document any anomalies or significant behaviors."
            ],
            [
                "Explore multi-level resource endpoints next.",
                "Look for endpoints that connect multiple resources in a sequence, such as `/resource/other_resource/another_resource`.",
                "Catalog each discovered endpoint that follows this structure, focusing on their hierarchical relationship.",
                "Systematically test these endpoints by adjusting identifiers as necessary, analyzing the response details to decode complex relationships or additional parameters."
            ],
            [
                "Finally, assess endpoints that utilize query parameters.",
                "Construct GET requests for endpoints by incorporating commonly used query parameters or those suggested in documentation.",
                "Persistently test these configurations to confirm that each query parameter effectively modifies the response, aiming to finalize the functionality of query parameters."
            ]
        ]

