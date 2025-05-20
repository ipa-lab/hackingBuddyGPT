import json
import os

from hackingBuddyGPT.utils.prompt_generation.information import PromptStrategy


class ConfigurationHandler(object):

    def __init__(self, config_file, strategy_string=None):
        self.config_file = config_file
        self.strategy_string = strategy_string

    def load(self, strategy_string=None):
        if self.config_file != "":
            if self.config_file != "":
                current_file_path = os.path.dirname(os.path.abspath(__file__))
                self.config_path = os.path.join(current_file_path, "configs", self.config_file)
        config = self._load_config()

        if "spotify" in self.config_path:
            os.environ['SPOTIPY_CLIENT_ID'] = config['client_id']
            os.environ['SPOTIPY_CLIENT_SECRET'] = config['client_secret']
            os.environ['SPOTIPY_REDIRECT_URI'] = config['redirect_uri']

        return config, self.get_strategy(strategy_string)

    def get_strategy(self, strategy_string=None):

        strategies = {
            "cot": PromptStrategy.CHAIN_OF_THOUGHT,
            "tot": PromptStrategy.TREE_OF_THOUGHT,
            "icl": PromptStrategy.IN_CONTEXT
        }
        if strategy_string:
            return strategies.get(strategy_string, PromptStrategy.IN_CONTEXT)

        return strategies.get(self.strategy_string, PromptStrategy.IN_CONTEXT)

    def _load_config(self, config_path=None):
        if config_path is None:
            config_path = self.config_path
        """Loads JSON configuration from the specified path."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
        with open(config_path, 'r') as file:
            return json.load(file)




    def _extract_config_values(self, config):
        token = config.get("token")
        host = config.get("host")
        description = config.get("description")
        correct_endpoints = config.get("correct_endpoints", {})
        query_params = config.get("query_params", {})
        return token, host, description, correct_endpoints, query_params


