import os
import requests

openapi_model : str = ''
openapi_key : str = ''

def openai_config():
    global openapi_model, openapi_key

    api_key = os.getenv('OPENAI_KEY')
    model = os.getenv('MODEL')

    if api_key != '' and model != '':
        openapi_model = model
        openapi_key = api_key
    else:
        raise Exception("please set OPENAI_KEY and MODEL through environment variables!")

def get_openai_response(cmd):
    global openapi_model, openapi_key

    headers = {"Authorization": f"Bearer {openapi_key}"}
    data = {'model': openapi_model, 'messages': [{'role': 'user', 'content': cmd}]}
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data).json()

    print(str(response))
    return response['choices'][0]['message']['content']
