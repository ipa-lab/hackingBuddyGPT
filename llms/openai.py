import openai
import os

def get_openai_response(model, cmd):
    openai.api_key = os.getenv("OPENAI_KEY")

    if model == '' and openai.api_key == '':
        raise Exception("please set OPENAI_KEY and MODEL through environment variables!")

    completion = openai.ChatCompletion.create(model=model, messages=[{"role": "user", "content" : cmd}])
    return completion.choices[0].message.content