from llms.openai_rest import get_openai_rest_connection_data
from llms.oobabooga import get_oobabooga_setup

# we do not need something fast (like a map)
connections = [
    get_openai_rest_connection_data(),
    get_oobabooga_setup()
]

def get_potential_llm_connections():
    return list(map(lambda x: x[0], connections))

def get_llm_connection(name, model, context_size):
    for i in connections:
        if i[0] == name:
            if i[1]() == True:
                return LLMConnection(name, model, context_size, i[2])
            else:
                print("Parameter for connection missing")
                return None
    print("Configured connection not found")
    return None

class LLMConnection:
    def __init__(self, conn, model, context_size, exec_query):
        self.conn = conn
        self.model = model
        self.context_size = context_size
        self.exec_query = exec_query
    
    def exec_query(self, query):
        return self.exec_query(self.model, self.context_size, query)
    
    def get_context_size(self):
        return self.context_size

    def output_metadata(self):
        return f"connection: {self.conn} using {self.model} with context-size {self.context_size}"
    
    def get_model(self) -> str:
        return self.model
    
    def get_context_size(self) -> int:
        return self.context_size