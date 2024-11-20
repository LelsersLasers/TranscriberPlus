import os
import subprocess

import flask
import flask_cors # type: ignore[import]

SVELTE_DIR = "../frontend/public"
UPLOAD_DIR = "./temp"
ALLOWED_EXTENSIONS = ["wav", "mp3", "mp4"]

import transcribe


def get_file_extension(filename):
	return filename.rsplit(".", 1)[1].lower()

def allowed_file(filename):
	return '.' in filename and get_file_extension(filename) in ALLOWED_EXTENSIONS


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
		print("Got request")

		file = flask.request.files["file"]
		
		if not file:
			return flask.jsonify({"error": "No file provided"})
		
		if not allowed_file(file.filename):
			return flask.jsonify({"error": "Invalid file type"})
		
		filename = file.filename

		print("Got file:", filename)

		os.makedirs(UPLOAD_DIR, exist_ok=True)

		filepath = os.path.join(UPLOAD_DIR, filename)
		file.save(filepath)

		print("Saved file to:", filepath)

		if get_file_extension(filename) == "mp4":
			print("Converting mp4 to wav")

			# ffmpeg -i input.mp4 -q:a 0 -map a audio.wav
			new_filename = filename.rsplit(".", 1)[0] + ".wav"
			new_filepath = os.path.join(UPLOAD_DIR, new_filename)

			command = f"ffmpeg -i {filepath} -q:a 0 -map a {new_filepath}".split()
			subprocess.run(command)
			
			os.remove(filepath)

			filename = new_filename
			filepath = new_filepath

			print("Converted mp4 to wav")


		print("Transcribing audio")
		# model_name = flask.request.form.get("model_name", "tiny.en")
		result = transcribe.transcribe_audio(filepath, "tiny.en")

		print("Transcription:", result)

		os.remove(filepath)

		print("Removed file")

		return flask.jsonify(result)


	app.run(port=5000, debug=True)

if __name__ == "__main__":
	run_server()