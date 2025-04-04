# GTFOBin: wireshark

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

This requires GUI interaction. Start Wireshark, then from the main menu, select “Tools” -> “Lua” -> “Evaluate”. A window opens that allows to execute `lua` code.

```
wireshark
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This technique can be used to write arbitrary files, i.e., the dump of one UDP packet.

After starting Wireshark, and waiting for the capture to begin, deliver the UDP packet, e.g., with `nc` (see below). The capture then stops and the packet dump can be saved:

1. 
select the only received packet;

2. 
right-click on “Data” from the “Packet Details” pane, and select “Export Packet Bytes…”;

3. 
choose where to save the packet dump.

```
PORT=4444
sudo wireshark -c 1 -i lo -k -f "udp port $PORT" &
echo 'DATA' | nc -u 127.127.127.127 "$PORT"
```