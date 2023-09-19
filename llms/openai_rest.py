import os
import requests

openai_model : str = 'gpt-3.5-turbo'
openai_key : str = 'none'

def get_openai_rest_connection_data():
    return "openai_rest", verify_config, get_openai_response

def verify_config():
    global openai_key, openai_model

    openai_key = os.getenv("OPENAI_KEY")
    if openai_key == '':
        raise Exception("please set OPENAI_KEY through environment variables!")
    
    return True

def get_openai_response(model, context_size, cmd):
    global openai_key

    headers = {"Authorization": f"Bearer {openai_key}"}
    data = {'model': model, 'messages': [{'role': 'user', 'content': cmd}]}

    retry = 3
    successfull = False
    response = None
    while retry >= 0 and not successfull:
        try:
            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, timeout=120)

            if response.status == 429:
                print("[RestAPI-Connector] running into rate-limits, waiting for a minute")
                response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, timeout=120)

            if response.status != 200:
                print("[Warning] REST API response code != 200")
                print(str(response))

            successfull = True
        except requests.exceptions.Timeout:
            print("Timeout while contacting LLM REST endpoint")
        retry -= 1

    # now extract the JSON status message
    # TODO: error handling..
    response = response.json()
    return response['choices'][0]['message']['content'], response['usage']['prompt_tokens'], response['usage']['completion_tokens']
