import os

from transcription import Transcription, TranscriptionState


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
	with_timestamps TEXT
);
"""

def make_table(db):
	db.executescript(CREATE_TABLES)

def update_state(db, base, state):
	db.execute("UPDATE transcriptions SET state = ? WHERE base = ?", (state, base))
	db.commit()

def reset_in_progress(db, upload_dir):
	cursor = db.execute("SELECT * FROM transcriptions WHERE state = ?", (TranscriptionState.CONVERTING,))
	transcriptions = [Transcription.from_dict(dict(row)) for row in cursor.fetchall()]

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

	# CONVERTING -> DOWNLOADED
	db.execute("UPDATE transcriptions SET state = ? WHERE state = ?", (TranscriptionState.DOWNLOADED, TranscriptionState.CONVERTING))
	db.commit()

	# TRANSCRIBING -> CONVERTED
	db.execute("UPDATE transcriptions SET state = ? WHERE state = ?", (TranscriptionState.CONVERTED, TranscriptionState.TRANSCRIBING))
	db.commit()