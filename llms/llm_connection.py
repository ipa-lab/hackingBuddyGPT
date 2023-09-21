from llms.openai_rest import get_openai_rest_connection_data
from llms.oobabooga import get_oobabooga_setup

# we do not need something fast (like a map)
connections = [
    get_openai_rest_connection_data(),
    get_oobabooga_setup()
]

def get_potential_llm_connections():
    return list(map(lambda x: x[0], connections))

def get_llm_connection(config):
    for i in connections:
        if i[0] == config.llm_connection:
            if i[1](config) == True:
                return LLMConnection(config, i[2])
            else:
                print("Parameter for connection missing")
                return None
    print("Configured connection not found")
    return None

class LLMConnection:
    def __init__(self, config, exec_query):
        self.conn = config.llm_connection
        self.model = config.model
        self.context_size = config.context_size
        self.exec_query = exec_query
    
    def exec_query(self, query):
        return self.exec_query(self.model, self.context_size, query)
    
    def get_context_size(self):
        return self.context_size
    
    def get_model(self) -> str:
        return self.model
    
    def get_context_size(self) -> int:
        return self.context_size