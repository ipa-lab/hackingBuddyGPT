#!/usr/bin/python

import os
import openai

from dotenv import load_dotenv
from mako.template import Template

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

mytemplate = Template(filename='templates/gpt_query.txt')

while True:

    cmd = mytemplate.render(user=initial_user, history=cmd_history.dump())
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
