import os
import subprocess

import flask
import flask_cors # type: ignore[import]
import flask_socketio # type: ignore[import]
import logging
import time

import whisper # type: ignore[import]

import util
import threading

import sql
import sqlite3

from transcription import Transcription, TranscriptionState
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
SVELTE_DIR = "../frontend/public"
UPLOAD_DIR = "./temp"
ALLOWED_EXTENSIONS = ["wav", "mp3", "mp4"]
MODEL_NAME = "tiny.en"
DATABASE = "./database.db"
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
currently_transcribing_lock = threading.Lock()
currently_transcribing = False

db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
db.row_factory = sqlite3.Row
db_lock = threading.Lock()

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
def convert(base: str):
	with db_lock:
		cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
		trans = Transcription.from_dict(dict(cursor.fetchone()))

	if trans.extension == "mp4":
		new_filename = f"{trans.base}.wav"
		new_filepath = os.path.join(UPLOAD_DIR, new_filename)

		download_filename = f"{trans.base}.{trans.extension}"
		download_filepath = os.path.join(UPLOAD_DIR, download_filename)

		command = f"ffmpeg -v 0 -y -i {download_filepath} -q:a 0 -map a {new_filepath}".split()
		subprocess.run(command)

		os.remove(download_filepath)

		trans.extension = "wav"

		with db_lock:
			db.execute(
				"UPDATE transcriptions SET extension = ? WHERE base = ?",
				(trans.extension, trans.base)
			)
			db.commit()

	trans.state = TranscriptionState.CONVERTED
	with db_lock:
		sql.update_state(db, trans.base, trans.state)

	emit_update()

	inc_process_loop_count()

def transcribe(base):
	global currently_transcribing

	with db_lock:
		cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
		trans = Transcription.from_dict(dict(cursor.fetchone()))

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

	with db_lock:
		db.execute(
			"UPDATE transcriptions SET state = ?, text = ?, with_timestamps = ? WHERE base = ?",
			(trans.state, trans.text, trans.with_timestamps, trans.base)
		)
		db.commit()

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
		
		with db_lock:
			cursor = db.execute("SELECT * FROM transcriptions WHERE state < ?", (TranscriptionState.TRANSCRIBED,))
			transcriptions = [Transcription.from_dict(dict(row)) for row in cursor.fetchall()]

		for trans in transcriptions:
			if trans.state == TranscriptionState.DOWNLOADED:
				trans.state = TranscriptionState.CONVERTING
				with db_lock:
					sql.update_state(db, trans.base, trans.state)
				t = threading.Thread(target=convert, args=(trans.base,))
				t.start()

			if trans.state == TranscriptionState.CONVERTED and not local_currently_transcribing:
				with currently_transcribing_lock:
					currently_transcribing = True
					local_currently_transcribing = True
				trans.state = TranscriptionState.TRANSCRIBING
				with db_lock:
					sql.update_state(db, trans.base, trans.state)
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

		process_loop_count = max(1, process_loop_count + 1)

		if not process_thread.is_alive():
			process_thread = threading.Thread(target=process)
			process_thread.start()
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
init_done = False

def init():
	global init_done

	if init_done: return
	init_done = True
	print("Initializing...")
	with db_lock:
		sql.make_table(db)
		sql.reset_in_progress(db, UPLOAD_DIR)
	util.make_folder(UPLOAD_DIR)
	inc_process_loop_count()

def emit_update():
	with db_lock:	
		cursor = db.execute("SELECT * FROM transcriptions WHERE state < ?", (TranscriptionState.TRANSCRIBED,))
		wip = [dict(row) for row in cursor.fetchall()]

		cursor = db.execute("SELECT * FROM transcriptions WHERE state = ?", (TranscriptionState.TRANSCRIBED,))
		done = [dict(row) for row in cursor.fetchall()]
	
	wip.sort(key=lambda x: x["state"], reverse=True)

	for l in [wip, done]:
		for trans in l:
			trans["state_str"] = TranscriptionState.to_str(trans["state"])

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

@app.route("/delete/<base>", methods=["DELETE"])
def delete(base):
	with db_lock:
		cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
		trans = Transcription.from_dict(dict(cursor.fetchone()))
	
	if trans.state in [TranscriptionState.CONVERTED, TranscriptionState.TRANSCRIBED]:
		with db_lock:
			db.execute("DELETE FROM transcriptions WHERE base = ?", (base,))
			db.commit()

		if trans.state == TranscriptionState.CONVERTED:
			filename = f"{trans.base}.{trans.extension}"
			filepath = os.path.join(UPLOAD_DIR, filename)

			try:
				os.remove(filepath)
			except FileNotFoundError:
				print(f"File not found: {filepath}")
		
		emit_update()
		return flask.jsonify({"success": True})
	
	return flask.jsonify({"error": "Cannot delete transcription in this state"})


@app.route("/upload/", methods=["POST"])
def upload():
	file = flask.request.files["file"]
	
	if not file:
		return flask.jsonify({"error": "No file provided"})
	
	if not util.allowed_file(file.filename, ALLOWED_EXTENSIONS):
		return flask.jsonify({"error": "Invalid file type"})
	
	trans = Transcription(file.filename)
	with db_lock:
		db.execute(
			"INSERT INTO transcriptions (base, original_filename, extension, state, text, with_timestamps) VALUES (?, ?, ?, ?, ?, ?)",
			trans.to_values()
		)
		db.commit()

	emit_update()

	download_filename = f"{trans.base}.{util.get_file_extension(file.filename)}"
	download_filepath = os.path.join(UPLOAD_DIR, download_filename)

	os.makedirs(UPLOAD_DIR, exist_ok=True)
	file.save(download_filepath)

	trans.state = TranscriptionState.DOWNLOADED

	with db_lock:
		sql.update_state(db, trans.base, trans.state)
		db.commit()

	emit_update()
	
	inc_process_loop_count()

	return flask.jsonify({"base": trans.base})


init()
sio.run(app, port=5000, debug=False)
#------------------------------------------------------------------------------#