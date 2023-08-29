import config
import requests


def get_openai_response(cmd):
    if config.model() == '' and config.openai_key() == '':
        raise Exception("please set OPENAI_KEY and MODEL through environment variables!")
    openapi_key = config.openai_key()
    openapi_model = config.model()

    headers = {"Authorization": f"Bearer {openapi_key}"}
    data = {'model': openapi_model, 'messages': [{'role': 'user', 'content': cmd}]}
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data).json()

    print(str(response))
    return response['choices'][0]['message']['content']
