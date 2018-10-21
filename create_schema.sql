CREATE TABLE squitters(
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

DROP VIEW IF EXISTS callsigns;

CREATE VIEW IF NOT EXISTS callsigns AS
  SELECT callsign, hex_ident, date(parsed_time) date_seen, max(parsed_time) last_seen, min(parsed_time) first_seen
    FROM squitters 
    WHERE callsign != ""
    GROUP BY callsign, hex_ident, date_seen;

DROP VIEW IF EXISTS locations;

CREATE VIEW IF NOT EXISTS locations AS
  SELECT hex_ident, parsed_time, lon, lat, altitude
    FROM squitters WHERE lat != "";

DROP VIEW IF EXISTS flights;

CREATE VIEW IF NOT EXISTS flights AS
  SELECT DISTINCT l.*, cs.callsign
    FROM locations l JOIN callsigns cs
      ON (l.hex_ident = cs.hex_ident
          and l.parsed_time <= strftime('%Y-%m-%dT%H:%M:%S',cs.last_seen, "10 minutes")
          and l.parsed_time >= strftime('%Y-%m-%dT%H:%M:%S',cs.first_seen,"-10 minutes"));

