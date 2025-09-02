from .llm_util import LLM, trim_result_front


class SlidingCliHistory:
    model: LLM = None
    maximum_target_size: int = 0
    sliding_history: str = ""
    last_output: str = ''

    def __init__(self, used_model: LLM):
        self.model = used_model
        self.maximum_target_size = self.model.context_size

    def add_command(self, cmd: str, output: str):
        self.sliding_history += f"$ {cmd}\n{output}"
        self.sliding_history = trim_result_front(self.model, self.maximum_target_size, self.sliding_history)

    def get_history(self, target_size: int) -> str:
        return trim_result_front(self.model, min(self.maximum_target_size, target_size), self.sliding_history)

    def add_command_only(self, cmd: str, output: str):
        self.sliding_history +=  f"$ {cmd}\n"
        self.last_output = output
        last_output_size = self.model.count_tokens(self.last_output)
        if self.maximum_target_size - last_output_size < 0:
            last_output_size = 0
            self.last_output = ''
        self.sliding_history = trim_result_front(self.model, self.maximum_target_size - last_output_size, self.sliding_history)

    def get_commands_and_last_output(self, target_size: int) -> str:
        return trim_result_front(self.model, min(self.maximum_target_size, target_size), self.sliding_history + self.last_output)