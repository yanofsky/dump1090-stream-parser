# dump1090 stream parser

This software takes a dump1090 stream and plops it into a sqlite database with a timestamp.

## Useage

You'll need a dump1090 instance running somewhere accessable on your network

If dump1090 is runing on your current machine running

```
python dump1090-stream-parser.py
```

will create and start populating a sqlite database named adsb_messages.db in your current directory

Stop the stream by hitting control + c. This will write any remaining uncommitted lines to the database and exit. 

###Complete usage and options

```
usage: dump1090-stream-parser.py [-h] [-l LOCATION] [-p PORT] [-d DATABASE]
                                 [--buffer-size BUFFER_SIZE]
                                 [--batch-size BATCH_SIZE]

A program to process dump1090 messages then insert them into a database

optional arguments:
  -h, --help            show this help message and exit
  -l LOCATION, --location LOCATION
                        This is the network location of your dump1090
                        broadcast. Defaults to localhost
  -p PORT, --port PORT  The port broadcasting in SBS-1 BaseStation format.
                        Defaults to 30003
  -d DATABASE, --database DATABASE
                        The location of a database file to use or create.
                        Defaults to adsb_messages.db
  --buffer-size BUFFER_SIZE
                        An integer of the number of bytes to read at a time
                        from the stream. Defaults to 100
  --batch-size BATCH_SIZE
                        An integer of the number of rows to write to the
                        database at a time. A lower number makes it more
                        likely that your database will be locked when you try
                        to query it. Defaults to 50
```

## examples

### Connecting to dump1090 instance running on a raspberry pi on your local network 

```
python dump1090-stream-parser.py -l raspberrypi.local
```

### Using a database in a different directory

```
python dump1090-stream-parser.py -d /path/to/database.db
```

### Write every record to the database immediately instead of batching insertions 
```
python dump1090-stream-parser.py --batch-size 1
```

### Read larger chunks from the stream
```
python dump1090-stream-parser.py --buffer-size 1024
```

### A combination
```
# connect to the local machine via ip address and save records in 20 line batches to todays_squitters.db
python dump1090-stream-parser.py -l 127.0.0.1 -d todays_squitters.db --batch-size 20
```