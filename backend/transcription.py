import util
import uuid

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
		t.extension = d["extension"]
		t.base = d["base"]
		t.state = d["state"]
		t.text = d["text"]
		t.with_timestamps = d["with_timestamps"]
		return t
	
	def to_values(self)-> tuple:
		return (self.base, self.original_filename, self.extension, self.state, self.text, self.with_timestamps)