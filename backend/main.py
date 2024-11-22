import os
import subprocess

import flask
import flask_cors # type: ignore[import]
import flask_socketio # type: ignore[import]
import logging
import uuid

import whisper # type: ignore[import]

import util
import threading

import sql
import sqlite3
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
SVELTE_DIR = "../frontend/public"
UPLOAD_DIR = "./temp"
ALLOWED_EXTENSIONS = ["wav", "mp3", "mp4"]
MODEL_NAME = "tiny.en"
DATABASE = "./database.db"
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
class TranscriptionState:
	INIT         = 0
	DOWNLOADED   = 1
	CONVERTING   = 2
	CONVERTED    = 3
	TRANSCRIBING = 4
	TRANSCRIBED  = 5

	@staticmethod
	def to_str(state: int):
		if state == TranscriptionState.INIT:
			return "Pending"
		elif state == TranscriptionState.DOWNLOADED:
			return "Downloaded"
		elif state == TranscriptionState.CONVERTING:
			return "Converting to WAV"
		elif state == TranscriptionState.CONVERTED:
			return "Waiting to transcribe"
		elif state == TranscriptionState.TRANSCRIBING:
			return "Transcribing"
		elif state == TranscriptionState.TRANSCRIBED:
			return "Transcribed"

class Transcription:
	def __init__(self, filename: str):
		self.original_filename = filename
		self.extension = util.get_file_extension(filename)

		self.base = uuid.uuid4().hex
		self.state = TranscriptionState.INIT

		self.text = ""
		self.with_timestamps = ""

	@classmethod
	def from_dict(cls, d: dict)-> 'Transcription':
		t = cls(d["original_filename"])
		t.base = d["base"]
		t.state = d["state"]
		t.text = d["text"]
		t.with_timestamps = d["with_timestamps"]
		return t
	
	def to_values(self)-> tuple:
		return (self.base, self.original_filename, self.extension, self.state, self.text, self.with_timestamps)
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
currently_transcribing_lock = threading.Lock()
currently_transcribing = False

thread_local_data = threading.local()

process_thread: threading.Thread = threading.Thread()
process_loop_count_lock = threading.Lock()
process_loop_count = 0
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
app = flask.Flask(__name__, static_folder=SVELTE_DIR)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
flask_cors.CORS(app)
sio = flask_socketio.SocketIO(app, cors_allowed_origins="*")
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
# TODO: use a context manager
def get_connection():
	if not hasattr(thread_local_data, "db"):
		thread_local_data.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
		thread_local_data.db.row_factory = sqlite3.Row
	return thread_local_data.db

def close_connection():
	if hasattr(thread_local_data, "db"):
		thread_local_data.db.close()
		del thread_local_data.db

def convert(base: str):
	db = get_connection()
	cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
	trans = Transcription.from_dict(dict(cursor.fetchone()))
	close_connection()

	if trans.extension == "mp4":
		new_filename = f"{trans.base}.wav"
		new_filepath = os.path.join(UPLOAD_DIR, new_filename)

		download_filename = f"{trans.base}.{trans.extension}"
		download_filepath = os.path.join(UPLOAD_DIR, download_filename)

		command = f"ffmpeg -v 0 -i {download_filepath} -q:a 0 -map a {new_filepath}".split()
		subprocess.run(command)

		os.remove(download_filepath)
		trans.extension = "wav"

		# db = get_connection()
		# trans.extension = "wav"
		# db.execute(
		# 	"UPDATE transcriptions SET extension = ? WHERE base = ?",
		# 	(trans.extension, trans.base)
		# )
		# db.commit()
		# close_connection()

	db = get_connection()
	trans.state = TranscriptionState.CONVERTED
	db.execute(
		"UPDATE transcriptions SET state = ?, extension = ? WHERE base = ?",
		(trans.state, trans.extension, trans.base)
	)
	db.commit()
	close_connection()

	emit_update()

	inc_process_loop_count()

def transcribe(base):
	global currently_transcribing

	db = get_connection()
	cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
	trans = Transcription.from_dict(dict(cursor.fetchone()))
	close_connection()

	print(trans.to_values())

	filename = f"{trans.base}.{trans.extension}"
	filepath = os.path.join(UPLOAD_DIR, filename)

	model = whisper.load_model(MODEL_NAME)
	result = model.transcribe(filepath, verbose=False)

	os.remove(filepath)

	trans.text = result["text"]
	trans.with_timestamps = ""
	for s in result["segments"]:
		start = util.format_time(s["start"])
		trans.with_timestamps += f"[{start}] {s['text'].strip()} <br />"

	trans.state = TranscriptionState.TRANSCRIBED

	db = get_connection()
	db.execute(
		"UPDATE transcriptions SET state = ?, text = ?, with_timestamps = ? WHERE base = ?",
		(trans.state, trans.text, trans.with_timestamps, trans.base)
	)
	db.commit()
	close_connection()

	emit_update()

	with currently_transcribing_lock:
		currently_transcribing = False

	inc_process_loop_count()


def process():
	global process_loop_count
	global currently_transcribing

	with process_loop_count_lock:
		local_process_loop_count = process_loop_count
	
	while local_process_loop_count > 0:
		with currently_transcribing_lock:
			local_currently_transcribing = currently_transcribing
		
		db = get_connection()
		cursor = db.execute("SELECT * FROM transcriptions WHERE state < ?", (TranscriptionState.TRANSCRIBED,))
		transcriptions = [Transcription.from_dict(dict(row)) for row in cursor.fetchall()]
		close_connection()

		wip = {trans.base: trans for trans in transcriptions}
		uuids = list(wip.keys())
		for uuid in uuids:
			trans = wip[uuid]

			if trans.state == TranscriptionState.DOWNLOADED:
				trans.state = TranscriptionState.CONVERTING
				db = get_connection()
				db.execute(
					"UPDATE transcriptions SET state = ? WHERE base = ?",
					(trans.state, trans.base)
				)
				db.commit()
				close_connection()
				t = threading.Thread(target=convert, args=(trans.base,))
				t.start()

			if trans.state == TranscriptionState.CONVERTED and not local_currently_transcribing:
				with currently_transcribing_lock:
						currently_transcribing = True
						local_currently_transcribing = True
				trans.state = TranscriptionState.TRANSCRIBING
				db = get_connection()
				db.execute(
					"UPDATE transcriptions SET state = ? WHERE base = ?",
					(trans.state, trans.base)
				)
				db.commit()
				close_connection()
				t = threading.Thread(target=transcribe, args=(trans.base,))
				t.start()

		emit_update()
		
		with currently_transcribing_lock:
			if local_currently_transcribing != currently_transcribing:
				with process_loop_count_lock:
					process_loop_count += 1
					local_process_loop_count = process_loop_count

		with process_loop_count_lock:
			process_loop_count -= 1
			local_process_loop_count = process_loop_count


def inc_process_loop_count():
	with process_loop_count_lock:
		global process_loop_count
		global process_thread

		process_loop_count += 1

		if not process_thread.is_alive():
			process_thread = threading.Thread(target=process)
			process_thread.start()
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
def init():
	db = get_connection()

	sql.make_table(db)
	sql.reset_in_progress(db)

	close_connection()

	util.make_folder(UPLOAD_DIR)
	
	inc_process_loop_count()

def emit_update():
	db = get_connection()
	
	cursor = db.execute("SELECT * FROM transcriptions WHERE state < ?", (TranscriptionState.TRANSCRIBED,))
	wip = [dict(row) for row in cursor.fetchall()]

	cursor = db.execute("SELECT * FROM transcriptions WHERE state = ?", (TranscriptionState.TRANSCRIBED,))
	done = [dict(row) for row in cursor.fetchall()]

	close_connection()

	for l in [wip, done]:
		for trans in l:
			trans["state"] = TranscriptionState.to_str(trans["state"])

	sio.emit("update", {
		"wip": wip,
		"done": done
	})


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
	if path and os.path.exists(os.path.join(app.static_folder, path)):
		return flask.send_from_directory(app.static_folder, path)
	return flask.send_from_directory(app.static_folder, 'index.html')

@sio.on("connect")
def connect():
	emit_update()

@app.route("/upload/", methods=["POST"])
def upload():
	file = flask.request.files["file"]
	
	if not file:
		return flask.jsonify({"error": "No file provided"})
	
	if not util.allowed_file(file.filename, ALLOWED_EXTENSIONS):
		return flask.jsonify({"error": "Invalid file type"})
	
	trans = Transcription(file.filename)
	db = get_connection()
	db.execute(
		"INSERT INTO transcriptions (base, original_filename, extension, state, text, with_timestamps) VALUES (?, ?, ?, ?, ?, ?)",
		trans.to_values()
	)
	db.commit()
	close_connection()

	emit_update()

	download_filename = f"{trans.base}.{util.get_file_extension(file.filename)}"
	download_filepath = os.path.join(UPLOAD_DIR, download_filename)

	os.makedirs(UPLOAD_DIR, exist_ok=True)
	file.save(download_filepath)

	trans.state = TranscriptionState.DOWNLOADED

	db = get_connection()
	db.execute(
		"UPDATE transcriptions SET state = ? WHERE base = ?",
		(TranscriptionState.DOWNLOADED, trans.base)
	)
	db.commit()
	close_connection()

	emit_update()
	
	inc_process_loop_count()

	return flask.jsonify({"base": trans.base})


init()
# app.run(port=5000, debug=True)
sio.run(app, port=5000, debug=True)
#------------------------------------------------------------------------------#