import openai
import config

def get_openai_response(cmd):

    if config.model() == '' and config.openai_key() == '':
        raise Exception("please set OPENAI_KEY and MODEL through environment variables!")

    openai.api_key = config.openai_key()

    completion = openai.ChatCompletion.create(model=config.model(), messages=[{"role": "user", "content" : cmd}])
    return completion.choices[0].message.content
