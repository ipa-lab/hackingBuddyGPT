import openai
import os

openapi_model : str = ''

def openai_config():
    global openapi_model

    api_key = os.getenv('OPENAI_KEY')
    model = os.getenv('MODEL')

    if api_key != '' and model != '':
        openai.api_key = api_key
        openapi_model = model
    else:
        raise Exception("please set OPENAI_KEY and MODEL through environment variables!")

def get_openai_response(cmd):
    completion = openai.ChatCompletion.create(model=openapi_model, messages=[{"role": "user", "content" : cmd}])
    return completion.choices[0].message.content
