import os
import requests

openai_model : str = 'gpt-3.5-turbo'
openai_key : str = 'none'

def get_openai_rest_connection_data():
    return "openai_rest", verify_config, get_openai_response

def verify_config():
    global openai_key, openai_model

    openai_key = os.getenv("OPENAI_KEY")
    openai_model = os.getenv("MODEL")

    if openai_model == '' or openai_key == '':
        raise Exception("please set OPENAI_KEY and MODEL through environment variables!")
    
    return True

def get_openai_response(cmd):
    global openai_key, openai_model

    headers = {"Authorization": f"Bearer {openai_key}"}
    data = {'model': openai_model, 'messages': [{'role': 'user', 'content': cmd}]}
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data).json()

    return response['choices'][0]['message']['content'], response['usage']['prompt_tokens'], response['usage']['completion_tokens']
