import os
import subprocess

import flask
import flask_cors # type: ignore[import]
import uuid

SVELTE_DIR = "../frontend/public"
UPLOAD_DIR = "./temp"
ALLOWED_EXTENSIONS = ["wav", "mp3", "mp4"]

import transcribe


def get_file_extension(filename):
	return filename.rsplit(".", 1)[1].lower()

def allowed_file(filename):
	return '.' in filename and get_file_extension(filename) in ALLOWED_EXTENSIONS

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{int(hours)}:{int(minutes):02}:{seconds:04.1f}"
    elif minutes > 0:
        return f"{int(minutes)}:{seconds:04.1f}"
    else:
        return f"{seconds:.1f}"


def run_server():
	app = flask.Flask(__name__, static_folder=SVELTE_DIR)
	flask_cors.CORS(app)

	@app.route('/', defaults={'path': ''})
	@app.route('/<path:path>')
	def serve(path):
		if path and os.path.exists(os.path.join(app.static_folder, path)):
			return flask.send_from_directory(app.static_folder, path)
		return flask.send_from_directory(app.static_folder, 'index.html')

	@app.route("/upload/", methods=["POST"])
	def upload():
		file = flask.request.files["file"]
		
		if not file:
			return flask.jsonify({"error": "No file provided"})
		
		if not allowed_file(file.filename):
			return flask.jsonify({"error": "Invalid file type"})
		
		input_filename = file.filename
		base = uuid.uuid4()
		filename = f"{base}.{get_file_extension(input_filename)}"

		os.makedirs(UPLOAD_DIR, exist_ok=True)

		filepath = os.path.join(UPLOAD_DIR, filename)
		file.save(filepath)

		if get_file_extension(filename) == "mp4":
			new_filename = f"{base}.wav"
			new_filepath = os.path.join(UPLOAD_DIR, new_filename)

			command = f"ffmpeg -v 0 -i {filepath} -q:a 0 -map a {new_filepath}".split()
			subprocess.run(command)
			
			os.remove(filepath)

			filename = new_filename
			filepath = new_filepath


		# model_name = flask.request.form.get("model_name", "tiny.en")
		result = transcribe.transcribe_audio(filepath, "tiny.en")

		os.remove(filepath)

		text = result["text"]
		with_timestamps = ""
		for s in result["segments"]:
			start = format_time(s["start"])
			with_timestamps += f"[{start}] {s['text'].strip()} <br />"

		data = {
			"text": text,
			"with_timestamps": with_timestamps
		}

		return flask.jsonify(data)


	app.run(port=5000, debug=True)

if __name__ == "__main__":
	run_server()