import whisper

def transcribe_audio(audio_file):
    model = whisper.load_model("tiny.en")
    result = model.transcribe(audio_file)
    return result["text"]

audio_file = "audio.wav"
transcription = transcribe_audio(audio_file)
print("Transcription:\n", transcription)
