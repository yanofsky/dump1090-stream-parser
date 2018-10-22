#!/usr/bin/env python
# encoding: utf-8

import socket
import datetime
import sqlite3
import argparse
import time

#defaults
HOST = "localhost"
PORT = 30003
DB = "adsb_messages.db"
BUFFER_SIZE = 100
BATCH_SIZE = 1
CONNECT_ATTEMPT_LIMIT = 10
CONNECT_ATTEMPT_DELAY = 5.0


def main():

	#set up command line options
	parser = argparse.ArgumentParser(description="A program to process dump1090 messages then insert them into a database")
	parser.add_argument("-l", "--location", type=str, default=HOST, help="This is the network location of your dump1090 broadcast. Defaults to %s" % (HOST,))
	parser.add_argument("-p", "--port", type=int, default=PORT, help="The port broadcasting in SBS-1 BaseStation format. Defaults to %s" % (PORT,))
	parser.add_argument("-d", "--database", type=str, default=DB, help="The location of a database file to use or create. Defaults to %s" % (DB,))
	parser.add_argument("--buffer-size", type=int, default=BUFFER_SIZE, help="An integer of the number of bytes to read at a time from the stream. Defaults to %s" % (BUFFER_SIZE,))
	parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="An integer of the number of rows to write to the database at a time. If you turn off WAL mode, a lower number makes it more likely that your database will be locked when you try to query it. Defaults to %s" % (BATCH_SIZE,))
	parser.add_argument("--connect-attempt-limit", type=int, default=CONNECT_ATTEMPT_LIMIT, help="An integer of the number of times to try (and fail) to connect to the dump1090 broadcast before qutting. Defaults to %s" % (CONNECT_ATTEMPT_LIMIT,))
	parser.add_argument("--connect-attempt-delay", type=float, default=CONNECT_ATTEMPT_DELAY, help="The number of seconds to wait after a failed connection attempt before trying again. Defaults to %s" % (CONNECT_ATTEMPT_DELAY,))

	# parse command line options
	args = parser.parse_args()

	# print args.accumulate(args.in)
	count_since_commit = 0
	count_total = 0
	count_failed_connection_attempts = 1

	# connect to database or create if it doesn't exist
	conn = sqlite3.connect(args.database)
	cur = conn.cursor()
	cur.execute('PRAGMA journal_mode=wal')

	# set up the table if neccassary
	cur.execute("""CREATE TABLE IF NOT EXISTS
		squitters(
			message_type TEXT,
			transmission_type INT,
			session_id TEXT,
			aircraft_id TEXT,
			hex_ident TEXT,
			flight_id TEXT,
			generated_date TEXT,
			generated_time TEXT,
			logged_date TEXT,
			logged_time TEXT,
			callsign TEXT,
			altitude INT,
			ground_speed INT,
			track INT,
			lat REAL,
			lon REAL,
			vertical_rate REAL,
			squawk TEXT,
			alert INT,
			emergency INT,
			spi INT,
			is_on_ground INT,
			parsed_time TEXT
		);
	""")

	cur.execute("""
			CREATE VIEW IF NOT EXISTS callsigns AS
			  SELECT callsign, hex_ident, date(parsed_time) date_seen, max(parsed_time) last_seen, min(parsed_time) first_seen
				FROM squitters
				WHERE callsign != ""
				GROUP BY callsign, hex_ident, date_seen;

	""")

	cur.execute("""
			CREATE VIEW IF NOT EXISTS locations AS
			  SELECT hex_ident, parsed_time, lon, lat, altitude
				FROM squitters WHERE lat != "";
	""")

	cur.execute("""
			CREATE VIEW IF NOT EXISTS flights AS
			  SELECT DISTINCT l.*, cs.callsign
				FROM locations l JOIN callsigns cs
				  ON (l.hex_ident = cs.hex_ident
					  and l.parsed_time <= strftime('%Y-%m-%dT%H:%M:%S',cs.last_seen, "10 minutes")
					  and l.parsed_time >= strftime('%Y-%m-%dT%H:%M:%S',cs.first_seen,"-10 minutes"));

	""")

	start_time = datetime.datetime.utcnow()

	# open a socket connection
	while count_failed_connection_attempts < args.connect_attempt_limit:
		try:
			s = connect_to_socket(args.location, args.port)
			count_failed_connection_attempts = 1
			print "Connected to dump1090 broadcast"
			break
		except socket.error:
			count_failed_connection_attempts += 1
			print "Cannot connect to dump1090 broadcast. Making attempt %s." % (count_failed_connection_attempts)
			time.sleep(args.connect_attempt_delay)
	else:
		quit()

	data_str = ""
	last_time = start_time

	try:
		#loop until an exception
		while True:
			#get current time
			cur_time = datetime.datetime.utcnow()
			ds = cur_time.isoformat()
			ts = cur_time.strftime("%H:%M:%S")

			# receive a stream message
			try:
				message = ""
				message = s.recv(args.buffer_size)
				data_str += message.strip("\n")
			except socket.error:
				# this happens if there is no connection and is delt with below
				pass

			if len(message) == 0:
				print ts, "No broadcast received. Attempting to reconnect"
				time.sleep(args.connect_attempt_delay)
				s.close()

				while count_failed_connection_attempts < args.connect_attempt_limit:
					try:
						s = connect_to_socket(args.location, args.port)
						count_failed_connection_attempts = 1
						print "Reconnected!"
						break
					except socket.error:
						count_failed_connection_attempts += 1
						print "The attempt failed. Making attempt %s." % (count_failed_connection_attempts)
						time.sleep(args.connect_attempt_delay)
				else:
					quit()

				continue

			# it is possible that more than one line has been received
			# so split it then loop through the parts and validate

			data = data_str.split("\n")

			for d in data:
				line = d.split(",")

				#if the line has 22 items, it's valid
				if len(line) == 22:

					# add the current time to the row
					line.append(ds)

					try:
						# add the row to the db
						cur.executemany("""INSERT INTO squitters
							(
								message_type,
								transmission_type,
								session_id,
								aircraft_id,
								hex_ident,
								flight_id,
								generated_date,
								generated_time,
								logged_date,
								logged_time,
								callsign,
								altitude,
								ground_speed,
								track,
								lat,
								lon,
								vertical_rate,
								squawk,
								alert,
								emergency,
								spi,
								is_on_ground,
								parsed_time
							)
							VALUES (""" + ", ".join(["?"] * len(line)) + ")", (line,))

						# increment counts
						count_total += 1
						count_since_commit += 1

						# commit the new rows to the database in batches
						if count_since_commit % args.batch_size == 0:
							conn.commit()
							if cur_time != last_time:
								print "averging %s rows per second, currently %s rows per second" % (float(count_total) / (cur_time - start_time).total_seconds(),float(count_since_commit) / (cur_time - last_time).total_seconds())
							else:
								print "averging %s rows per second" % (float(count_total) / (cur_time - start_time).total_seconds(),)
							if count_since_commit > args.batch_size:
								print ts, "All caught up, %s rows, successfully written to database" % (count_since_commit)
							count_since_commit = 0
							last_time = cur_time

					except sqlite3.OperationalError:
						print ts, "Could not write to database, will try to insert %s rows on next commit" % (count_since_commit + args.batch_size,)


					# since everything was valid we reset the stream message
					data_str = ""
				else:
					# the stream message is too short, prepend to the next stream message
					data_str = d
					continue

	except KeyboardInterrupt:
		print "\n%s Closing connection" % (ts,)
		s.close()

		conn.commit()
		conn.close()
		print ts, "%s squitters added to your database" % (count_total,)

	except sqlite3.ProgrammingError:
		print "Error with ", line
		quit()

def connect_to_socket(loc,port):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((loc, port))
	return s

if __name__ == '__main__':
	main()
