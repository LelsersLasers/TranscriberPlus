import transcribe
import pprint

audio_file = "audio.wav"
res = transcribe.transcribe_audio(audio_file, "tiny.en")

text = res["text"]
print("Transcription:\n", text)

segments = res["segments"]
print("\n\nSegments:")
pprint.pprint(segments)