import sqlite3
import flask

from transcription import TranscriptionState


CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS transcriptions (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	original_filename TEXT,
	extension TEXT,
	base TEXT,
	state INTEGER,
	text TEXT,
	with_timestamps TEXT
);
"""

def make_table(db):
	db.executescript(CREATE_TABLES)

def update_state(db, base, state):
	db.execute("UPDATE transcriptions SET state = ? WHERE base = ?", (state, base))
	db.commit()

def reset_in_progress(db):
	# CONVERTING -> DOWNLOADED
	db.execute("UPDATE transcriptions SET state = ? WHERE state = ?", (TranscriptionState.DOWNLOADED, TranscriptionState.CONVERTING))
	db.commit()

	# TRANSCRIBING -> CONVERTED
	db.execute("UPDATE transcriptions SET state = ? WHERE state = ?", (TranscriptionState.CONVERTED, TranscriptionState.TRANSCRIBING))
	db.commit()