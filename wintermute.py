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
whytemplate = Template(filename='templates/why.txt')
furthertemplate = Template(filename='templates/further_information.txt')

while True:

    cmd = mytemplate.render(user=initial_user, history=cmd_history.dump())
    logs.warning("openai-prompt", cmd)

    print("now thinking..")
    next_cmd = get_openai_response(cmd)
    logs.warning("openai-next-command", next_cmd)

    if False:
        # disable this for now, it's tragic because the AI won't tell me why it had chosen something
        print("now thinking why did I choose this? can we put both questions into a single prompt?")
        why = whytemplate.render(user=initial_user, history=cmd_history.dump(), next_cmd=next_cmd)
        why_response = get_openai_response(why)
        logs.warning("why", why_response)


    print("running the command..")
    resp = conn.run(next_cmd)
    logs.warning("server-output", resp)

    print("now thinking about more exploits")
    vulns = furthertemplate.render(user=initial_user, next_cmd=next_cmd, resp=resp)
    print(vulns)
    vulns_resp = get_openai_response(vulns)
    logs.warning("vulns", vulns_resp)

    cmd_history.append(next_cmd, resp)
