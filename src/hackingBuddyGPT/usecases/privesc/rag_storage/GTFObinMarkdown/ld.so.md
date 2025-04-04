# GTFOBin: ld.so

`ld.so` is the Linux dynamic linker/loader, its filename and location might change across distributions. The proper path is can be obtained with:

```
$ strings /proc/self/exe | head -1
/lib64/ld-linux-x86-64.so.2

```

It’s worth noting that the spawned process will be the loader, not the target executable, this might aid evasion. See https://shyft.us/posts/20230526_linux_command_proxy.html for more information.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
/lib/ld.so /bin/sh
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which ld.so) .

./ld.so /bin/sh -p
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo /lib/ld.so /bin/sh
```