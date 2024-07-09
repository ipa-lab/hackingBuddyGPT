from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model


class LLMHandler(object):
    def __init__(self, llm, capabilities):
        self.llm = llm
        self._capabilities = capabilities

    def call_llm(self, prompt):
        return self.llm.instructor.chat.completions.create_with_completion(model=self.llm.model, messages=prompt, response_model=capabilities_to_action_model(self._capabilities))
