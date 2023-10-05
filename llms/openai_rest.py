import os
import requests
import time

openai_key : str = ''
openai_url : str = ''

RATE_LIMIT_BACKOFF = 60

def get_openai_rest_connection_data():
    return "openai_rest", verify_config, get_openai_response

def verify_config(config):
    global openai_key, openai_url

    openai_key = os.getenv("OPENAI_KEY")
    if openai_key == '' or openai_key == None:
        raise Exception("please set OPENAI_KEY through environment variables!")
    
    openai_url = f'{config.llm_server_base_url}/v1/chat/completions'
    return True

OPENAI_TIMEOUT=240
def get_openai_response(model, context_size, cmd):
    global openai_key, openai_url

    headers = {"Authorization": f"Bearer {openai_key}"}
    data = {'model': model, 'messages': [{'role': 'user', 'content': cmd}]}

    retry = 3
    successfull = False
    response = None
    while retry >= 0 and not successfull:
        try:
            response = requests.post(openai_url, headers=headers, json=data, timeout=OPENAI_TIMEOUT)

            if response.status_code == 429:
                print(f"[RestAPI-Connector] running into rate-limits, waiting for {RATE_LIMIT_BACKOFF} seconds")
                time.sleep(RATE_LIMIT_BACKOFF)
                response = requests.post(openai_url, headers=headers, json=data, timeout=OPENAI_TIMEOUT)

            if response.status_code != 200:
                print("[Warning] REST API response code != 200")
                print(str(response))
                print("reponse reason:" + str(response.json()))
                # better let if fail for now
                # return "error from openAI gateway", '0', '0'
            successfull = True
        except requests.exceptions.ConnectionError:
            print("Connection error! Retrying in 5 seconds..")
            time.sleep(5)
        except requests.exceptions.Timeout:
            print("Timeout while contacting LLM REST endpoint")
        retry -= 1

    # now extract the JSON status message
    # TODO: error handling..
    response = response.json()
    return response['choices'][0]['message']['content'], response['usage']['prompt_tokens'], response['usage']['completion_tokens']
