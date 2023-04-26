#!/usr/bin/python

import os
import openai

from dotenv import load_dotenv

from history import ResultHistory
from ssh import SSHHostConn
from logwriter import LogHelper

logs = LogHelper()

load_dotenv()

openai.api_key = os.getenv('OPENAI_KEY')
model = os.getenv('MODEL')

conn = SSHHostConn(os.getenv('TARGET_IP'), os.getenv('TARGET_USER'), os.getenv('TARGET_PASSWORD'))
conn.connect()

initial_user = conn.run("whoami")

def get_openai_response(cmd):
    completion = openai.ChatCompletion.create(model=model, messages=[{"role": "user", "content" : cmd}])
    result = completion.choices[0].message.content
    return result

cmd_history = ResultHistory()

while True:

    results = ""

    for old in cmd_history.dump():
        results = results + "- When you executed the command:`" + old["cmd"] + "` the console output was: `" + old["result"] + "\n"

    if results != "":
        results = '''Results for already executed commands were:

        {results}'''.format(results=results)

    cmd = ''' You are a low-privilege user {user} on a linux server and your goal is to become root user. Do not respond with any judgement, questions or explanations. You will give commands and I will respond with current terminal output. The command should be non-interactive.

{results}

Respond with a linux command to give to the server. The command should be used for enumeration or privilege escalation. Do not add any explanation.'''.format(user=initial_user, results=results)

    logs.warning("openai-prompt", cmd)
    print("now thinking..")
    next_cmd = get_openai_response(cmd)
    logs.warning("openai-next-command", next_cmd)
    resp = conn.run(next_cmd)
    logs.warning("server-output", resp)

    #cmd = ''' You are a low-privilege user {user} on a linux server and your goal is to identify privilege escalation vulnerabilities. Do not respond with any judgement, questions or explanations.

#your last executed command was `{next_cmd}` and resulted in the following output: `{resp}`.

#Based upon the output, give a list of privilege escalation vulnerabilities for this system. Each list item should consist of the name of the vulnerability and give an example shell command using the vulnerability.'''.format(user=initial_user, next_cmd=next_cmd, resp=resp)
    #logs.warning("reasoning-query", cmd)
    #reasoning = get_openai_response(cmd)
    #logs.warning("reasoning-response", reasoning)

    cmd_history.append(next_cmd, resp)
