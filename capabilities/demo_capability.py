from typing import Dict, List, Union

# the basic idea is to have an instanciated class for each capability
class DemoCapability:
    # NOTE: hopefully two hierarchy levels are enough for config
    def __init__(self, config: Dict[str, Union[str, Dict[str, str]]]):
        self.config = config

    # TODO: use something form self.config to actually provide customized description
    def describe(self) -> str:
        return "This is a demo capability. You can give it an command and will retrieve the reverted command."

    # TODO: use self.config to configure something, I assume we will use this for creating network connections in other capabilities
    def configure(self):
        pass

    # execute the task
    def execute(self, arg: str) -> List[str]:
        return [arg[::-1], "some success"]