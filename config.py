import os

def model():
    return os.getenv("MODEL")

def context_size():
    return int(os.getenv("CONTEXT_SIZE"))

def target_ip():
    return os.getenv('TARGET_IP')

def target_password():
    return os.getenv("TARGET_PASSWORD")

def target_user():
    return os.getenv('TARGET_USER')

def llm_connection():
    return os.getenv("LLM_CONNECTION")

def max_rounds():
    return int(os.getenv("MAX_ROUNDS"))