import os

from dotenv import load_dotenv

def check_config():
    load_dotenv()

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

def openai_key():
    return os.getenv('OPENAI_KEY')

def oobabooga_url():
    return os.getenv('OOBABOOGA_URL')