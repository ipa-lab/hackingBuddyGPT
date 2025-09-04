from typing import Optional, List, Dict

from hackingBuddyGPT.utils.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.utils.prompt_generation.prompts.task_planning import (
    TaskPlanningPrompt,
)
from hackingBuddyGPT.utils.web_api.custom_datatypes import Prompt


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

    def __init__(self, context: PromptContext, prompt_helper, prompt_file) -> None:
        """
        Initializes the TreeOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
            round (int): The round number for the prompt generation process.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.TREE_OF_THOUGHT, prompt_file=prompt_file)

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
            tree_of_thought_steps = self._get_documentation_steps(common_steps, move_type, self.get_documentation_steps())
            tree_of_thought_steps = [
                                        "Imagine three experts each proposing one step at a time. If an expert realizes their step was incorrect, they leave. The question is:"] + tree_of_thought_steps

        elif self.context == PromptContext.PENTESTING:
            tree_of_thought_steps = self._get_pentesting_steps(move_type)
        else:
            steps = self.parse_prompt_file()

            tree_of_thought_steps = self._get_documentation_steps(common_steps, move_type, steps)


            tree_of_thought_steps = ([
                                        "Imagine three experts each proposing one step at a time. If an expert realizes their step was incorrect, they leave. The question is:"] +
                                     tree_of_thought_steps)
        if hint:
            tree_of_thought_steps.append(hint)


        return self.prompt_helper._check_prompt(previous_prompt=previous_prompt, steps=tree_of_thought_steps)


    def transform_into_prompt_structure(self, test_case, purpose):
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
            "purpose": purpose,
            "root": f"Objective: {test_case['objective']}",
            "steps": [],
            "assessments": [],
            "path": test_case.get("path")
        }
        counter = 0
        # Process steps in the test case as potential steps
        for i, step in enumerate(test_case["steps"]):
            if counter < len(test_case["security"]):
                security = test_case["security"][counter]
            else:
                security = test_case["security"][0]

            if len(test_case["steps"]) > 1:
                if counter < len(test_case["expected_response_code"]):
                    expected_response_code = test_case["expected_response_code"][counter]

                else:
                    expected_response_code = test_case["expected_response_code"]

                print(f'COunter: {counter}')
                token = test_case["token"][counter]
                path = test_case["path"][counter]
            else:
                expected_response_code = test_case["expected_response_code"]
                token = test_case["token"][0]
                path = test_case["path"][0]


            step = """Imagine three different experts are answering this question.
                      All experts will write down 1 step of their thinking,
                      then share it with the group.
                      Then all experts will go on to the next step, etc.
                      If any expert realises they're wrong at any point then they leave.
                      The question is : """ + step


            # Define a branch representing a single reasoning path
            branch = {
                "purpose": purpose,
                "step": step,
                "security": security,
                "expected_response_code": expected_response_code,
                "conditions": {
                    "if_successful": "No Vulnerability found.",
                    "if_unsuccessful": "Vulnerability found."
                },
                "token": token,
                "path": path
            }
            # Add branch to the tree
            transformed_case["steps"].append(branch)



        return transformed_case


    def transform_test_case_to_string(self, tree_of_thought, character):
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

        # Handle steps
        if character == "steps":
            result.append("Tree of Thought:\n")
            for idx, branch in enumerate(tree_of_thought["steps"], start=1):
                result.append(f"  Branch {idx}:\n")
                result.append(f"    Step: {branch['step']}\n")
                result.append(f"    Security: {branch['security']}\n")
                result.append(f"    Expected Response Code: {branch['expected_response_code']}\n")
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

        Dynamic Branching: Conditional steps allow for the creation of alternative paths ("sub-steps") based on intermediate outcomes. This enables the prompt to pivot when initial strategies don’t fully succeed.

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

            # Add the structured Tree of Thought with steps and checkpoints to the final prompts dictionary
            tot_prompts[purpose] = tree_steps

        return tot_prompts

    def get_documentation_steps(self):
        return [
            [
                f"Objective: Identify all accessible endpoints via GET requests for {self.prompt_helper.host}. {self.prompt_helper._description}"],
            [
                "Start by querying root-level resource endpoints.",
                "Focus on sending GET requests only to those endpoints that consist of a single path component directly following the root.",
                "For instance, paths should look like '/users' or '/products', with each representing a distinct resource type.",
                "Ensure to explore new paths that haven't been previously tested to maximize coverage.",
            ],
            [
                "Next, move to instance-level resource endpoints.",
                "Identify and list endpoints formatted as `/resource/id`, where 'id' represents a dynamic parameter.",
                "Attempt to query these endpoints to validate whether the 'id' parameter correctly retrieves individual resource instances.",
                "Consider testing with various ID formats, such as integers, longs, or base62 encodings like '6rqhFgbbKwnb9MLmUQDhG6'."
            ],
            ["Now, move to query Subresource Endpoints.",
             "Identify subresource endpoints of the form `/resource/other_resource`.",
             "Query these endpoints to check if they return data related to the main resource without requiring an `id` parameter."
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

    def generate_documentation_steps(self, steps):
        return  self.get_documentation_steps()
