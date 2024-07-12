from hackingBuddyGPT.capabilities.capability import capabilities_to_action_model

class LLMHandler(object):
    """
    LLMHandler is a class responsible for managing interactions with a large language model (LLM).
    It handles the execution of prompts and the management of created objects based on the capabilities.

    Attributes:
        llm (object): The large language model to interact with.
        _capabilities (dict): A dictionary of capabilities that define the actions the LLM can perform.
        created_objects (dict): A dictionary to keep track of created objects by their type.
    """

    def __init__(self, llm, capabilities):
        """
        Initializes the LLMHandler with the specified LLM and capabilities.

        Args:
            llm (object): The large language model to interact with.
            capabilities (dict): A dictionary of capabilities that define the actions the LLM can perform.
        """
        self.llm = llm
        self._capabilities = capabilities
        self.created_objects = {}

    def call_llm(self, prompt):
        """
        Calls the LLM with the specified prompt and retrieves the response.

        Args:
            prompt (list): The prompt messages to send to the LLM.

        Returns:
            response (object): The response from the LLM.
        """
        return self.llm.instructor.chat.completions.create_with_completion(
            model=self.llm.model,
            messages=prompt,
            response_model=capabilities_to_action_model(self._capabilities)
        )

    def add_created_object(self, created_object, object_type):
        """
        Adds a created object to the dictionary of created objects, categorized by object type.

        Args:
            created_object (object): The object that was created.
            object_type (str): The type/category of the created object.
        """
        if object_type not in self.created_objects:
            self.created_objects[object_type] = []
        if len(self.created_objects[object_type]) < 7:
            self.created_objects[object_type].append(created_object)

    def get_created_objects(self):
        """
        Retrieves the dictionary of created objects and prints its contents.

        Returns:
            dict: The dictionary of created objects.
        """
        print(f'created_objects: {self.created_objects}')
        return self.created_objects
