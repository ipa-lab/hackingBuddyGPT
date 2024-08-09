from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompt_information import PromptStrategy, PromptContext
from hackingBuddyGPT.usecases.web_api_testing.prompt_generation.prompts.basic_prompt import BasicPrompt


class ChainOfThoughtPrompt(BasicPrompt):
    def __init__(self, context, prompt_helper):
        super().__init__(context, prompt_helper, PromptStrategy.CHAIN_OF_THOUGHT)

    def generate_prompt(self, round, hint, previous_prompt):
        common_steps = self.get_common_steps()
        http_phase = {10: "PUT", 15: "DELETE"}

        chain_of_thought_steps = self.get_chain_of_thought_steps(round ,common_steps,http_phase)

        if hint:
            chain_of_thought_steps.append(hint)

        return self.prompt_helper.check_prompt(
            previous_prompt=previous_prompt, steps=chain_of_thought_steps)

    def get_common_steps(self):
        return [
            "Identify common data structures returned by various endpoints and define them as reusable schemas. Determine the type of each field (e.g., integer, string, array) and define common response structures as components that can be referenced in multiple endpoint definitions.",
            "Create an OpenAPI document including metadata such as API title, version, and description, define the base URL of the API, list all endpoints, methods, parameters, and responses, and define reusable schemas, response types, and parameters.",
            "Ensure the correctness and completeness of the OpenAPI specification by validating the syntax and completeness of the document using tools like Swagger Editor, and ensure the specification matches the actual behavior of the API.",
            "Refine the document based on feedback and additional testing, share the draft with others, gather feedback, and make necessary adjustments. Regularly update the specification as the API evolves.",
            "Make the OpenAPI specification available to developers by incorporating it into your API documentation site and keep the documentation up to date with API changes."
        ]

    def get_chain_of_thought_steps(self,round, common_steps,  http_phase):
            if self.context == PromptContext.DOCUMENTATION:
                if round <= 5:
                    return self.prompt_helper.get_initial_steps(common_steps)
                elif round <= 10:
                    phase = http_phase.get(min(x for x in http_phase.keys() if round <= x))
                    return self.prompt_helper.get_phase_steps(phase, common_steps)
                else:
                    return self.prompt_helper.get_endpoints_needing_help()
            else:
                if round == 0:
                    return ["Let's think step by step."]
                elif round <= 20:
                    focus_phases = ["endpoints", "HTTP method GET", "HTTP method POST and PUT", "HTTP method DELETE"]
                    return [f"Just focus on the {focus_phases[round // 5]} for now."]
                else:
                    return ["Look for exploits."]
