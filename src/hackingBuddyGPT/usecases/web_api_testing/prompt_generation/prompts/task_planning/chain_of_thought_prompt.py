from typing import List, Optional

from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.information.prompt_information import (
    PromptContext,
    PromptPurpose,
    PromptStrategy,
)
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.task_planning.task_planning_prompt import (
    TaskPlanningPrompt,
)


class ChainOfThoughtPrompt(TaskPlanningPrompt):
    """
    A class that generates prompts using the chain-of-thought strategy.

    This class extends the BasicPrompt abstract base class and implements
    the generate_prompt method for creating prompts based on the
    chain-of-thought strategy.

    Attributes:
        context (PromptContext): The context in which prompts are generated.
        prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        explored_steps (List[str]): A list of steps that have already been explored in the chain-of-thought strategy.
        purpose (Optional[PromptPurpose]): The purpose of the current prompt.
    """

    def __init__(self, context: PromptContext, prompt_helper):
        """
        Initializes the ChainOfThoughtPrompt with a specific context and prompt helper.

        Args:
            context (PromptContext): The context in which prompts are generated.
            prompt_helper (PromptHelper): A helper object for managing and generating prompts.
        """
        super().__init__(context=context, prompt_helper=prompt_helper, strategy=PromptStrategy.CHAIN_OF_THOUGHT)

    def generate_prompt(
            self, move_type: str, hint: Optional[str], previous_prompt: Optional[str], turn: Optional[int]
    ) -> str:
        """
        Generates a prompt using the chain-of-thought strategy. Provides the steps for the chain-of-thought strategy based on the current context.
        Args:
            move_type (str): The type of move to generate.
            hint (Optional[str]): An optional hint to guide the prompt generation.
            previous_prompt (Optional[str]): The previous prompt content based on the conversation history.
            turn (Optional[int]): The current turn of the chain-of-thought strategy.

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

    def _get_pentesting_steps(self, move_type: str, common_step: Optional[str] = "") -> List[str]:
        """
        Provides the steps for the chain-of-thought strategy when the context is pentesting.

        Args:
            move_type (str): The type of move to generate.
            common_step (Optional[str]): A list of common steps for generating prompts.

        Returns:
            List[str]: A list of steps for the chain-of-thought strategy in the pentesting context.
        """
        if move_type == "explore" and self.pentesting_information.init_steps(self.prompt_helper.current_endpoint):
            purpose = list(self.pentesting_information.explore_steps.keys())[0]
            steps = self.pentesting_information.explore_steps[purpose]

            # Transform steps into hierarchical conditional CoT
            transformed_steps = self.transform_to_hierarchical_conditional_cot({purpose: [steps]})

            # Extract the CoT for the current purpose
            cot_steps = transformed_steps[purpose]

            # Process steps one by one, with memory of explored steps and conditional handling
            for step in cot_steps:
                if step not in self.explored_steps:
                    self.explored_steps.append(step)

                    # Apply common steps if provided
                    if common_step:
                        step = common_step + step

                    # Remove the processed step from explore_steps
                    if len(self.pentesting_information.explore_steps[purpose]) > 0:
                        del self.pentesting_information.explore_steps[purpose][0]
                    else:
                        del self.pentesting_information.explore_steps[purpose]  # Clean up if all steps are processed

                    print(f'Prompt: {step}')
                    return step

        else:
            return ["Look for exploits."]

    def transform_to_hierarchical_conditional_cot(self, prompts):
        """
        Transforms prompts into a hybrid of Hierarchical and Conditional Chain-of-Thought.
### Explanation and Justification

This **Hierarchical and Conditional Chain-of-Thought (CoT)** design improves reasoning by combining structured phases with adaptable steps.

1. **Hierarchical Phases**:
   - **Explanation**: Each phase breaks down the problem into focused tasks.
   - **Justification**: Wei et al. (2022) show that phased structures improve model comprehension and accuracy.

2. **Conditional Steps**:
   - **Explanation**: Steps include conditional paths to adjust based on outcomes (proceed, retry, refine).
   - **Justification**: Zhou et al. (2022) found conditional prompts enhance problem-solving, especially for complex tasks.

3. **Dynamic Branching and Assessments**:
   - **Explanation**: Outcome-based branching and checkpoints ensure readiness to move forward.
   - **Justification**: Xie et al. (2023) support this approach in their Tree of Thought (ToT) framework, showing it boosts adaptive problem-solving.

### Summary

This method uses **Hierarchical and Conditional CoT** to enhance structured, adaptive reasoning, aligning with research supporting phased goals, dynamic paths, and iterative adjustments for complex tasks.

        Args:
            prompts (Dict[PromptPurpose, List[List[str]]]): Dictionary of prompts organized by purpose and steps.

        Returns:
            Dict[PromptPurpose, List[str]]: A dictionary with each key as a PromptPurpose and each value as a list of
                                            chain-of-thought prompts structured in hierarchical and conditional phases.
        """
        cot_prompts = {}

        for purpose, steps_list in prompts.items():
            phase_prompts = []
            phase_count = 1

            # Phase division: Each set of steps_list corresponds to a phase in the hierarchical structure
            for steps in steps_list:
                # Start a new phase
                phase_prompts.append(f"Phase {phase_count}: Task Breakdown")

                step_count = 1
                for step in steps:
                    # Add hierarchical structure for each step
                    phase_prompts.append(f"    Step {step_count}: {step}")

                    # Integrate conditional CoT checks based on potential outcomes
                    phase_prompts.append(f"        If successful: Proceed to Step {step_count + 1}.")
                    phase_prompts.append(
                        f"        If unsuccessful: Adjust previous step or clarify, then repeat Step {step_count}.")

                    # Increment step count for the next step in the current phase
                    step_count += 1

                # Assessment point at the end of each phase
                phase_prompts.append("    Assess: Review outcomes of all steps in this phase.")
                phase_prompts.append("    If phase objectives are met, proceed to the next phase.")
                phase_prompts.append("    If phase objectives are not met, re-evaluate and repeat necessary steps.")

                # Move to the next phase
                phase_count += 1

            # Final assessment
            phase_prompts.append("Final Assessment: Review all phases to confirm the primary objective is fully met.")
            cot_prompts[purpose] = phase_prompts

        return cot_prompts
