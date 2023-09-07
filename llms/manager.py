from llms.openai_rest import get_openai_rest_connection_data
from llms.oobabooga import get_oobabooga_setup

# we do not need something fast (like a map)
connections = [
    get_openai_rest_connection_data(),
    get_oobabooga_setup()
]

def get_llm_connection(name):
    for i in connections:
        if i[0] == name:
            if i[1]() == True:
                return i[2]
            else:
                print("Parameter for connection missing")
                return None
    print("Configured connection not found")
    return None