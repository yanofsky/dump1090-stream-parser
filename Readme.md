# dump1090 stream parser

This software takes a [dump1090](https://github.com/antirez/dump1090) stream of [ADS-B](https://en.wikipedia.org/wiki/Automatic_dependent_surveillance_%E2%80%93_broadcast) messages and plops them into a sqlite database with a timestamp.

## Usage

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
                                 [--connect-attempt-limit CONNECT_ATTEMPT_LIMIT]
                                 [--connect-attempt-delay CONNECT_ATTEMPT_DELAY]

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
                        to query it. Defaults to 1
  --connect-attempt-limit CONNECT_ATTEMPT_LIMIT
                        An integer of the number of times to try (and fail) to
                        connect to the dump1090 broadcast before qutting.
                        Defaults to 10
  --connect-attempt-delay CONNECT_ATTEMPT_DELAY
                        The number of seconds to wait after a failed
                        connection attempt before trying again. Defaults to
                        5.0
```

## Examples

Connecting to dump1090 instance running on a raspberry pi on your local network 

```
python dump1090-stream-parser.py -l raspberrypi.local
```

Using a database in a different directory

```
python dump1090-stream-parser.py -d /path/to/database.db
```

Write every record to the database immediately instead of batching insertions 
```
python dump1090-stream-parser.py --batch-size 1
```

Read larger chunks from the stream
```
python dump1090-stream-parser.py --buffer-size 1024
```

Connect to the local machine via ip address and save records in 20 line batches to todays_squitters.db
```
python dump1090-stream-parser.py -l 127.0.0.1 -d todays_squitters.db --batch-size 20
```

## Using the data
One issue with the core table `squitters` is that not all data appears
in all rows.  Not every row will have a latitude and longitude, and not
every row will have the callsign associated with an aircraft.  To help
make this data more useful, there are several convience views in the
default database schema:

### Callsigns VIEW

The view `callsigns` provides a per day mapping of callsigns to the
hex_ident that should be present in every message. Callsigns are (mostly)
human readable identifiers... usually the flight number for commercial
flights (e.g. UAL1601), or the registration number ("N number" in the US)
for private flights.

Although in most cases there will be a unique hex_ident for each callsign
(and vice versa) this is not always the case.  Sometimes an airline will
switch which aircraft is servicing a multi-leg flight, or the crew will
switch to a different ADSB radio during flight, and this will change
the hex_ident for that callsign.  Also, sometimes an idividual hex_ident
will be associated with more than one callsign, since the same aircraft
might serve several commercial flights in one day.  To help with this
confusion, there are `first_seen` and `last_seen` columns which will
help narrow down which times a particular callsign was associated with
a particular hex_ident.

For example, say you want to know when FedEx flights were seen in your area:
```
sqlite> select callsign, hex_ident, date_seen, first_seen, last_seen from callsigns where callsign like 'FDX%' limit 10;
FDX1167 |A8F63B|2018-10-16|2018-10-16T12:03:50.762491|2018-10-16T12:08:02.342313
FDX1167 |AA01E7|2018-10-17|2018-10-17T11:23:47.560089|2018-10-17T11:26:42.926003
FDX12   |AC1E56|2018-10-16|2018-10-16T05:46:00.927919|2018-10-16T05:48:25.557328
FDX12   |AC5FD6|2018-10-17|2018-10-17T06:38:02.982087|2018-10-17T06:41:12.678365
FDX1213 |A9C1C5|2018-10-17|2018-10-17T02:26:48.864018|2018-10-17T02:29:33.611975
FDX1268 |A841F5|2018-10-17|2018-10-17T02:43:15.714889|2018-10-17T02:43:15.714889
FDX1345 |A0B5C5|2018-10-17|2018-10-17T02:03:56.482701|2018-10-17T02:07:00.170058
FDX1413 |A69C03|2018-10-17|2018-10-17T12:44:06.227662|2018-10-17T12:47:16.271459
FDX1419 |A75659|2018-10-17|2018-10-17T11:26:14.485112|2018-10-17T11:28:44.356821
FDX1419 |A7617E|2018-10-16|2018-10-16T11:53:06.121191|2018-10-16T11:56:36.611446
```

### Locations VIEW

The view `locations` provides a list of locations (latitude, longitude
and altitude) mapped to the hex_ident and time the entry was parsed. Not
every hex_ident is guaranteed to be associated with a callsign, but most
will be.

For example, If you wanted to know where the flight FDX1167 went on October 16th:
```
sqlite> select hex_ident, parsed_time, lon, lat, altitude from locations where hex_ident = 'A8F63B' limit 10;
A8F63B|2018-10-16T12:03:44.667583|-121.84311|37.60638|4650
A8F63B|2018-10-16T12:03:49.321162|-121.84871|37.60648|4575
A8F63B|2018-10-16T12:03:52.465988|-121.8524|37.60652|4525
A8F63B|2018-10-16T12:03:53.579999|-121.85375|37.60657|4525
A8F63B|2018-10-16T12:03:54.038653|-121.85427|37.60657|4500
A8F63B|2018-10-16T12:03:57.774146|-121.85866|37.60666|4475
A8F63B|2018-10-16T12:04:16.189721|-121.88023|37.60695|4350
A8F63B|2018-10-16T12:04:16.779088|-121.88089|37.60695|4350
A8F63B|2018-10-16T12:04:17.892429|-121.88221|37.60693|4350
A8F63B|2018-10-16T12:04:18.352539|-121.88279|37.60693|4350
```

### Flights VIEW

The view `flights` joins up the previous two views to attempt to provide
a unified view of particular flights.

For example, in the previous case we needed find the hex_ident of a
particular flight, but with this view you can do both steps in one:

```
sqlite> select callsign, parsed_time, lon, lat, altitude from flights where callsign like 'FDX1345%' limit 10;
FDX1345 |2018-10-17T02:03:49.862699|-122.26971|37.68855|4575
FDX1345 |2018-10-17T02:03:50.846821|-122.26846|37.6892|4625
FDX1345 |2018-10-17T02:03:53.466993|-122.26523|37.69088|4800
FDX1345 |2018-10-17T02:03:55.105746|-122.26316|37.69199|4925
FDX1345 |2018-10-17T02:03:55.499516|-122.26264|37.69221|4950
FDX1345 |2018-10-17T02:03:56.416630|-122.26153|37.69281|5025
FDX1345 |2018-10-17T02:03:58.119922|-122.25942|37.69391|5150
FDX1345 |2018-10-17T02:03:58.578940|-122.25884|37.69418|5200
FDX1345 |2018-10-17T02:04:02.052030|-122.25449|37.69647|5475
FDX1345 |2018-10-17T02:04:04.739817|-122.25114|37.69819|5675
```

The only limitation is that it will only show locations for a flight
that fall between the 10 minutes before first_seen and 10 minutes after
last_seen timestamps in the callsigns view.  This helps avoid issues
when a particular hex_ident is associated with more than one callsign.
