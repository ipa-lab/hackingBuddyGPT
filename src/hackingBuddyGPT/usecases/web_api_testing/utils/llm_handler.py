from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model


class LLMHandler(object):
    def __init__(self, llm, capabilities):
        self.llm = llm
        self._capabilities = capabilities
        self.created_objects = {}

    def call_llm(self, prompt):
        return self.llm.instructor.chat.completions.create_with_completion(model=self.llm.model, messages=prompt, response_model=capabilities_to_action_model(self._capabilities))

    def add_created_object(self, created_object, object_type):
        if object_type not in self.created_objects:
            self.created_objects[object_type] = []
        if len(self.created_objects[object_type]) < 7:
            self.created_objects[object_type].append(created_object)

    def get_created_objects(self):
        print(f'created_objects: {self.created_objects}')
        return self.created_objects

