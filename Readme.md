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

The view `callsigns` provides a mapping of callsigns to the hex_ident
that should be present in every message. Callsigns are (mostly) human
readable identifiers... usually the flight identifier for commercial
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
sqlite> select * from callsigns where callsign like "FDX%";
FDX1117 |A8F63B|2018-10-16T03:42:18.329565|2018-10-16T03:42:18.329565
FDX1219 |A03B91|2018-10-16T02:20:18.612135|2018-10-16T02:12:46.242506
FDX1268 |A76535|2018-10-16T03:31:58.391159|2018-10-16T03:31:58.391159
FDX1345 |A0B97C|2018-10-16T02:23:24.985153|2018-10-16T02:19:59.279895
FDX1804 |A90EDE|2018-10-16T04:52:38.946034|2018-10-16T04:49:27.591450
FDX1813 |ACFC74|2018-10-16T02:33:28.539816|2018-10-16T02:29:01.560380
FDX1818 |ADC5A6|2018-10-16T04:04:24.114816|2018-10-16T04:01:18.789950
FDX1837 |A07BB3|2018-10-16T04:56:03.145089|2018-10-16T04:51:52.484677
FDX1839 |ACC262|2018-10-16T04:37:24.964137|2018-10-16T04:33:34.945958
FDX2642 |A8EB16|2018-10-16T02:35:41.701467|2018-10-16T02:28:09.004902
```

### Locations VIEW

The view `locations` provides a list of locations (latitude, longitude
and altitude) mapped to the hex_ident and time the entry was parsed. Not
every hex_ident is guaranteed to be associated with a callsign, but most
will be.

For example, If you wanted to know where the flight FDX1117 went:
```
sqlite> select hex_ident, parsed_time, lon, lat, altitude from locations where hex_ident = 'A8F63B';
A8F63B|2018-10-16T03:40:55.757156|-122.12934|37.89267|13375
A8F63B|2018-10-16T03:41:08.339089|-122.1042|37.89483|14025
A8F63B|2018-10-16T03:41:14.433657|-122.092|37.89619|14400
A8F63B|2018-10-16T03:41:25.115451|-122.07055|37.89867|15050
A8F63B|2018-10-16T03:42:12.300014|-121.97115|37.90997|16925
A8F63B|2018-10-16T03:42:23.963731|-121.94514|37.91265|17450
A8F63B|2018-10-16T03:42:25.996247|-121.94053|37.91309|17550
A8F63B|2018-10-16T03:42:44.017090|-121.89952|37.91708|18350
```

### Flgihts VIEW

The view `flights` joins up the previous two views to attempt to provide
a unified view of particular flights.

For example, in the previous case we needed find the hex_ident of a
particular flight, but with this view you can do both steps in one:

```
sqlite> select callsign, parsed_time, lon, lat, altitude from flights where callsign like "FDX1837%" limit 10;
FDX1837 |2018-10-16T04:51:52.876237|-121.85408|37.54103|5350
FDX1837 |2018-10-16T04:51:53.859459|-121.85563|37.54121|5325
FDX1837 |2018-10-16T04:51:55.759206|-121.8585|37.54154|5300
FDX1837 |2018-10-16T04:51:56.677004|-121.85987|37.54168|5275
FDX1837 |2018-10-16T04:51:58.577340|-121.86274|37.54201|5250
FDX1837 |2018-10-16T04:51:59.560406|-121.86423|37.54215|5225
FDX1837 |2018-10-16T04:52:00.478720|-121.86567|37.5423|5225
FDX1837 |2018-10-16T04:52:03.754648|-121.8705|37.54284|5200
FDX1837 |2018-10-16T04:52:05.589905|-121.87327|37.54317|5175
FDX1837 |2018-10-16T04:52:07.622230|-121.87629|37.5435|5150
```

The only limitation is that it will only show locations for a flight that
fall between the first_seen and last_seen timestamps in the callsigns
view.  This helps avoid issues when a particular hex_ident is associated
with more than one callsign.
