import whisper

def transcribe_audio(audio_file):
    model = whisper.load_model("tiny.en")
    result = model.transcribe(audio_file, word_timestamps=True, verbose=True)
    return result

audio_file = "audio.wav"
res = transcribe_audio(audio_file)

text = res["text"]
print("Transcription:\n", text)
