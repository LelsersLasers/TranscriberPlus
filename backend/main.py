print("Starting...")

import os
import subprocess

import flask
import flask_cors # type: ignore[import]
import flask_socketio # type: ignore[import]
import logging

import requests

import whisper_callback.whisper as whisper

import util
# import threading
import multiprocessing

import sql

from transcription import Transcription, TranscriptionState
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
PORT = 3004

SVELTE_DIR = "../frontend/public"
UPLOAD_DIR = "./temp"
ALLOWED_EXTENSIONS = ["wav", "mp3", "mp4"]
DATABASE = "./database.db"
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
manager = multiprocessing.Manager()

currently_transcribing_lock = multiprocessing.Lock()
currently_transcribing = manager.Value("b", False)

process_thread_going_lock = multiprocessing.Lock()
process_thread_going = manager.Value("b", False)
process_loop_count_lock = multiprocessing.Lock()
process_loop_count = manager.Value("i", 0)

server_init = multiprocessing.Lock()
server_init.acquire()
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
def convert(base: str):
	with sql.get_db(DATABASE) as db:
		cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
		trans = Transcription.from_dict(dict(cursor.fetchone()))

	error = False

	if trans.extension == "mp4":
		new_filename = f"{trans.base}.wav"
		new_filepath = os.path.join(UPLOAD_DIR, new_filename)

		download_filename = f"{trans.base}.{trans.extension}"
		download_filepath = os.path.join(UPLOAD_DIR, download_filename)

		command = f"ffmpeg -v 0 -y -i {download_filepath} -q:a 0 -map a {new_filepath}".split()
		subprocess.run(command)

		os.remove(download_filepath)

		trans.extension = "wav"

		with sql.get_db(DATABASE) as db:
			db.execute(
				"UPDATE transcriptions SET extension = ? WHERE base = ?",
				(trans.extension, trans.base)
			)
			db.commit()

		if not os.path.exists(new_filepath):
			error = True
			print(f"Error converting {new_filename} to {new_filename}")

			with sql.get_db(DATABASE) as db:
				sql.update_state(db, trans.base, TranscriptionState.ERROR)

	if not error:
		trans.state = TranscriptionState.CONVERTED
		with sql.get_db(DATABASE) as db:
			sql.update_state(db, trans.base, trans.state)

	make_emit_request()

	inc_process_loop_count()

def transcribe(base):
	global currently_transcribing

	with sql.get_db(DATABASE) as db:
		cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
		trans = Transcription.from_dict(dict(cursor.fetchone()))

	filename = f"{trans.base}.{trans.extension}"
	filepath = os.path.join(UPLOAD_DIR, filename)

	try:
		def callback(current, total, eta):
			percent = round(current / total * 100)
			eta = round(eta)
			with sql.get_db(DATABASE) as db:
				db.execute(
					"UPDATE transcriptions SET percent = ?, eta = ? WHERE base = ?",
					(percent, eta, base)
				)
				db.commit()
			make_emit_request()

		model = whisper.load_model(trans.model)
		result = model.transcribe(filepath, language=trans.language, verbose=False, callback=callback)

		os.remove(filepath)

		trans.text = result["text"]
		trans.with_timestamps = ""
		for s in result["segments"]:
			start = util.format_time(s["start"])
			trans.with_timestamps += f"[{start}] {s['text'].strip()} <br />"

		trans.state = TranscriptionState.TRANSCRIBED

		with sql.get_db(DATABASE) as db:
			db.execute(
				"UPDATE transcriptions SET state = ?, text = ?, with_timestamps = ? WHERE base = ?",
				(trans.state, trans.text, trans.with_timestamps, trans.base)
			)
			db.commit()
	except Exception as e:
		print(f"Error transcribing {filename}: {e}")

		os.remove(filepath)

		with sql.get_db(DATABASE) as db:
			sql.update_state(db, trans.base, TranscriptionState.ERROR)

	make_emit_request()

	with currently_transcribing_lock:
		currently_transcribing.set(False)

	inc_process_loop_count()


def loop():
	global process_thread_going
	global process_loop_count
	global currently_transcribing

	print("\n\nProcess\n\n")

	with process_thread_going_lock:
		process_thread_going.set(True)

	with process_loop_count_lock:
		local_process_loop_count = process_loop_count.get()
	
	while local_process_loop_count > 0:
		print(f"\n\nProcess Loop: {local_process_loop_count}\n\n")
		with currently_transcribing_lock:
			local_currently_transcribing = currently_transcribing.get()
		
		with sql.get_db(DATABASE) as db:
			cursor = db.execute("SELECT * FROM transcriptions WHERE state < ?", (TranscriptionState.TRANSCRIBED,))
			transcriptions = [Transcription.from_dict(dict(row)) for row in cursor.fetchall()]

		for trans in transcriptions:
			if trans.state == TranscriptionState.DOWNLOADED:
				trans.state = TranscriptionState.CONVERTING
				with sql.get_db(DATABASE) as db:
					sql.update_state(db, trans.base, trans.state)
				p = multiprocessing.Process(target=convert, args=(trans.base,))
				p.start()

			if trans.state == TranscriptionState.CONVERTED and not local_currently_transcribing:
				with currently_transcribing_lock:
					currently_transcribing.set(True)
					local_currently_transcribing = True
				trans.state = TranscriptionState.TRANSCRIBING
				with sql.get_db(DATABASE) as db:
					sql.update_state(db, trans.base, trans.state)
				p = multiprocessing.Process(target=transcribe, args=(trans.base,))
				p.start()

		make_emit_request()
		
		with currently_transcribing_lock:
			if local_currently_transcribing != currently_transcribing.get():
				with process_loop_count_lock:
					process_loop_count.set(process_loop_count.get() + 1)
					local_process_loop_count = process_loop_count.get()

		with process_loop_count_lock:
			process_loop_count.set(process_loop_count.get() - 1)
			local_process_loop_count = process_loop_count.get()

	with process_thread_going_lock:
		process_thread_going.set(False)


def inc_process_loop_count():
	global process_thread_going
	global process_loop_count

	server_init.acquire()
	print("\n\nSERVER INIT\n\n")
	server_init.release()

	print(f"\n\nInc Process Loop Count. going: {process_thread_going.get()}, count: {process_loop_count.get()}\n\n")

	with process_loop_count_lock:
		process_loop_count.set(max(1, process_loop_count.get() + 1))

		with process_thread_going_lock:
			if not process_thread_going.get():
				p = multiprocessing.Process(target=loop)
				p.start()


def make_emit_request():
	url = f"http://localhost:{PORT}/emit"
	print(f"\n\n{url}\n\n")
	requests.get(url)
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
def run_server():
	app = flask.Flask(__name__, static_folder=SVELTE_DIR)
	log = logging.getLogger('werkzeug')
	log.setLevel(logging.ERROR)
	flask_cors.CORS(app)
	sio = flask_socketio.SocketIO(app, cors_allowed_origins="*")

	def init():
		print("Initializing...")
		with sql.get_db(DATABASE) as db:
			sql.make_table(db)
			sql.reset_in_progress(db, UPLOAD_DIR)
		util.make_folder(UPLOAD_DIR)
		# inc_process_loop_count()
		p = multiprocessing.Process(target=inc_process_loop_count)
		p.start()

	def emit_update():
		with sql.get_db(DATABASE) as db:
			cursor = db.execute("SELECT * FROM transcriptions WHERE state < ?", (TranscriptionState.TRANSCRIBED,))
			wip = [dict(row) for row in cursor.fetchall()]

			cursor = db.execute("SELECT * FROM transcriptions WHERE state = ?", (TranscriptionState.TRANSCRIBED,))
			done = [dict(row) for row in cursor.fetchall()]
		
		wip.sort(key=lambda x: x["state"], reverse=True)
		done.reverse()

		all = wip + done

		for trans in all:
			trans["state_str"] = TranscriptionState.to_str(trans["state"])

		sio.emit("update", {
			"transcriptions": all
		})

	@app.route('/emit', methods=["GET"])
	def emit():
		print("/emit")
		emit_update()

		return flask.jsonify({"success": True})

	@app.route('/', defaults={'path': ''})
	@app.route('/<path:path>')
	def serve(path):
		if path and os.path.exists(os.path.join(app.static_folder, path)):
			print(path)
			return flask.send_from_directory(app.static_folder, path)
		print("index.html")
		return flask.send_from_directory(app.static_folder, 'index.html')

	@sio.on("connect")
	def connect():
		emit_update()

	@app.route("/delete/<base>", methods=["DELETE"])
	def delete(base):
		print("/delete")

		with sql.get_db(DATABASE) as db:
			cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
			trans = Transcription.from_dict(dict(cursor.fetchone()))
		
		if trans.state in [TranscriptionState.ERROR, TranscriptionState.CONVERTED, TranscriptionState.TRANSCRIBED]:
			with sql.get_db(DATABASE) as db:
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
		
		return flask.jsonify({"error": "Cannot delete or cancel transcription in this state"})


	@app.route("/start/", methods=["POST"])
	def start():
		print("/start")

		filename = flask.request.form.get("filename")

		if not util.allowed_file(filename, ALLOWED_EXTENSIONS):
			return flask.jsonify({"error": "Invalid file type. Accepted types: " + ", ".join(ALLOWED_EXTENSIONS)})

		trans = Transcription(filename)
		with sql.get_db(DATABASE) as db:
			db.execute(
				"""INSERT INTO transcriptions (base, original_filename, model, language, extension, state, text, with_timestamps, percent, eta)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
				trans.to_values()
			)
			db.commit()

		emit_update()

		return flask.jsonify({
			"success": True,
			"base": trans.base
		})


	@app.route("/upload/", methods=["POST"])
	def upload():
		print("/upload")

		file = flask.request.files["file"]

		base = flask.request.form.get("base")
		model = flask.request.form.get("model")
		language = flask.request.form.get("language")

		if not file:
			return flask.jsonify({"error": "No file provided"})
		
		if not util.allowed_file(file.filename, ALLOWED_EXTENSIONS):
			return flask.jsonify({"error": "Invalid file type. Accepted types: " + ", ".join(ALLOWED_EXTENSIONS)})
		
		with sql.get_db(DATABASE) as db:
			cursor = db.execute("SELECT * FROM transcriptions WHERE base = ?", (base,))
			trans = Transcription.from_dict(dict(cursor.fetchone()))

		trans.model = model
		trans.language = language

		with sql.get_db(DATABASE) as db:
			db.execute(
				"UPDATE transcriptions SET model = ?, language = ? WHERE base = ?",
				(trans.model, trans.language, trans.base)
			)
			db.commit()


		download_filename = f"{trans.base}.{util.get_file_extension(file.filename)}"
		download_filepath = os.path.join(UPLOAD_DIR, download_filename)

		os.makedirs(UPLOAD_DIR, exist_ok=True)
		file.save(download_filepath)

		trans.state = TranscriptionState.DOWNLOADED

		with sql.get_db(DATABASE) as db:
			sql.update_state(db, trans.base, trans.state)
			db.commit()

		emit_update()
		
		inc_process_loop_count()

		return flask.jsonify({"success": True})

	init()
	server_init.release()
	sio.run(app, host="0.0.0.0", port=3004, debug=False, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
	run_server()
#------------------------------------------------------------------------------#
