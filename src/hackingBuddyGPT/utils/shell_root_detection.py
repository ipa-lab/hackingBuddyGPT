import re

GOT_ROOT_REGEXPs = [re.compile("^# $"), re.compile("^bash-[0-9]+.[0-9]# $")]


def got_root(hostname: str, output: str) -> bool:
    for i in GOT_ROOT_REGEXPs:
        if i.fullmatch(output):
            return True

    return output.startswith(f"root@{hostname}:")
