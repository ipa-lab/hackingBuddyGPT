import re

def remove_wrapping_characters(cmd:str, wrappers:str) -> str:
    if cmd[0] == cmd[-1] and cmd[0] in wrappers:
        print("will remove a wrapper from: " + cmd)
        return remove_wrapping_characters(cmd[1:-1], wrappers)
    return cmd

# often the LLM produces a wrapped command
def cmd_output_fixer(cmd:str) -> str:

    if len(cmd) < 2:
        return cmd

    cmd = cmd.replace("<<CMD>>", "")
    cmd = cmd.replace("<<SUCCESS>>", "")
    cmd = cmd.lstrip(" \n")

    stupidity = re.compile(r"^[ \n\r]*```.*\n(.*)\n```$", re.MULTILINE)
    result = stupidity.search(cmd)
    if result:
        print("this would have been captured by the multi-line regex 1")
        cmd = result.group(1)
        print("new command: " + cmd)
    stupidity = re.compile(r"^[ \n\r]*~~~.*\n(.*)\n~~~$", re.MULTILINE)
    result = stupidity.search(cmd)
    if result:
        print("this would have been captured by the multi-line regex 2")
        cmd = result.group(1)
        print("new command: " + cmd)
    stupidity = re.compile(r"^[ \n\r]*~~~.*\n(.*)\n~~~$", re.MULTILINE)

    cmd = remove_wrapping_characters(cmd, "`'\"")

    if cmd.startswith("$ "):
        cmd = cmd[2:]
    
    return cmd
