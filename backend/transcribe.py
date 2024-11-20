import whisper # type: ignore[import]

def transcribe_audio(audio_filename, model_name):
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_filename, verbose=False)
    return result

# import transcribe
# import pprint

# audio_file = "audio.wav"
# res = transcribe.transcribe_audio(audio_file, "tiny.en")

# text = res["text"]
# print("Transcription:\n", text)

# segments = res["segments"]
# print("\n\nSegments:")
# pprint.pprint(segments)