import os
import sqlite3
from transcription import Transcription, TranscriptionState

import contextlib


CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS transcriptions (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	original_filename TEXT,
	model TEXT,
	language TEXT,
	extension TEXT,
	base TEXT,
	state INTEGER,
	text TEXT,
	with_timestamps TEXT,
	percent INTEGER,
	eta INTEGER
);
"""

@contextlib.contextmanager
def get_db(database: str):
    db = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()

def make_table(db: sqlite3.Connection):
	db.executescript(CREATE_TABLES)

def update_state(db: sqlite3.Connection, base: str, state: int):
	db.execute("UPDATE transcriptions SET state = ? WHERE base = ?", (state, base))
	db.commit()

def reset_in_progress(db: sqlite3.Connection, upload_dir: str):
	cursor = db.execute("SELECT * FROM transcriptions WHERE state = ?", (TranscriptionState.CONVERTING,))
	transcriptions = [Transcription.from_dict(dict(row)) for row in cursor.fetchall()]

	print("Deleting partially converted files:")
	for trans in transcriptions: print(trans.to_values())

	for trans in transcriptions:
		# Delete wav file
		filename = f"{trans.base}.wav"
		filepath = os.path.join(upload_dir, filename)
		print(f"Deleting {filepath}")

		try:
			os.remove(filepath)
		except FileNotFoundError:
			print(f"File not found: {filepath}")

	# INIT -> deleted
	cursor = db.execute("SELECT * FROM transcriptions WHERE state = ?", (TranscriptionState.INIT,))
	transcriptions = [Transcription.from_dict(dict(row)) for row in cursor.fetchall()]

	print("Deleting partially downloaded files:")
	for trans in transcriptions:
		filepath = os.path.join(upload_dir, trans.original_filename)

		print(f"Deleting {filepath}")
		try:
			os.remove(filepath)
		except FileNotFoundError:
			print(f"File not found: {filepath}")

	db.execute("DELETE FROM transcriptions WHERE state = ?", (TranscriptionState.INIT,))

		
	# CONVERTING -> DOWNLOADED
	db.execute("UPDATE transcriptions SET state = ? WHERE state = ?", (TranscriptionState.DOWNLOADED, TranscriptionState.CONVERTING))
	db.commit()

	# TRANSCRIBING -> CONVERTED
	db.execute("UPDATE transcriptions SET state = ? WHERE state = ?", (TranscriptionState.CONVERTED, TranscriptionState.TRANSCRIBING))
	db.commit()
