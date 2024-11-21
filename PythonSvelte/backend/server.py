import os
import subprocess

import flask
import flask_cors # type: ignore[import]
import uuid

import whisper # type: ignore[import]

import util
import threading
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
SVELTE_DIR = "../frontend/public"
UPLOAD_DIR = "./temp"
ALLOWED_EXTENSIONS = ["wav", "mp3", "mp4"]
MODEL_NAME = "tiny.en"
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

		self.base = uuid.uuid4()
		self.state = TranscriptionState.INIT

		self.text = ""
		self.with_timestamps = ""
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
wip_lock = threading.Lock()
wip_transcriptions: dict[uuid.UUID, Transcription] = {}

done_lock = threading.Lock()
done_transcriptions: dict[uuid.UUID, Transcription] = {}

currently_transcribing_lock = threading.Lock()
currently_transcribing = False

process_thread: threading.Thread = threading.Thread()
process_loop_count_lock = threading.Lock()
process_loop_count = 0
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
def convert(trans: Transcription):
	if trans.extension == "mp4":
		new_filename = f"{trans.base}.wav"
		new_filepath = os.path.join(UPLOAD_DIR, new_filename)

		download_filename = f"{trans.base}.{trans.extension}"
		download_filepath = os.path.join(UPLOAD_DIR, download_filename)

		command = f"ffmpeg -v 0 -i {download_filepath} -q:a 0 -map a {new_filepath}".split()
		subprocess.run(command)

		os.remove(download_filepath)
		trans.extension = "wav"

	trans.state = TranscriptionState.CONVERTED

	inc_process_loop_count()

def transcribe(trans: Transcription):
	global currently_transcribing

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
		
		with wip_lock:
			uuids = list(wip_transcriptions.keys())
			for uuid in uuids:
				trans = wip_transcriptions[uuid]

				if trans.state == TranscriptionState.TRANSCRIBED:
					with done_lock:
						done_transcriptions[uuid] = trans
					del wip_transcriptions[uuid]
				
				if trans.state == TranscriptionState.DOWNLOADED:
					trans.state = TranscriptionState.CONVERTING
					t = threading.Thread(target=convert, args=(trans,))
					t.start()

				if trans.state == TranscriptionState.CONVERTED and not local_currently_transcribing:
					with currently_transcribing_lock:
						currently_transcribing = True
					trans.state = TranscriptionState.TRANSCRIBING
					t = threading.Thread(target=transcribe, args=(trans,))
					t.start()

		
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
def full_clean():
	for filename in os.listdir(UPLOAD_DIR):
		filepath = os.path.join(UPLOAD_DIR, filename)
		os.remove(filepath)
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
def run_server():
	app = flask.Flask(__name__, static_folder=SVELTE_DIR)
	flask_cors.CORS(app)

	@app.route('/', defaults={'path': ''})
	@app.route('/<path:path>')
	def serve(path):
		if path and os.path.exists(os.path.join(app.static_folder, path)):
			return flask.send_from_directory(app.static_folder, path)
		return flask.send_from_directory(app.static_folder, 'index.html')
	
	@app.route("/status/")
	def status():
		wip = [] # [{'base': str, 'state': str, filename: str}, ...]
		with wip_lock:
			for uuid in wip_transcriptions:
				trans = wip_transcriptions[uuid]
				wip.append({
					"base": str(uuid),
					"state": TranscriptionState.to_str(trans.state),
					"filename": trans.original_filename
				})

		done = [] # [{'base': str, 'text': str, 'with_timestamps': str, 'filename': str}, ...]
		with done_lock:
			for uuid in done_transcriptions:
				trans = done_transcriptions[uuid]
				done.append({
					"base": str(uuid),
					"text": trans.text,
					"with_timestamps": trans.with_timestamps,
					"filename": trans.original_filename
				})

		return flask.jsonify({
			"wip": wip,
			"done": done
		})

	@app.route("/upload/", methods=["POST"])
	def upload():
		file = flask.request.files["file"]
		
		if not file:
			return flask.jsonify({"error": "No file provided"})
		
		if not util.allowed_file(file.filename, ALLOWED_EXTENSIONS):
			return flask.jsonify({"error": "Invalid file type"})
		
		trans = Transcription(file.filename)
		with wip_lock:
			wip_transcriptions[trans.base] = trans

		download_filename = f"{trans.base}.{util.get_file_extension(file.filename)}"
		download_filepath = os.path.join(UPLOAD_DIR, download_filename)

		os.makedirs(UPLOAD_DIR, exist_ok=True)
		file.save(download_filepath)

		trans.state = TranscriptionState.DOWNLOADED
		
		inc_process_loop_count()

		return flask.jsonify({"base": trans.base})


	app.run(port=5000, debug=True)
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
if __name__ == "__main__":
	full_clean()
	run_server()
#------------------------------------------------------------------------------#