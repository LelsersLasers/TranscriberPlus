import whisper

def transcribe_audio(audio_filename, model_name):
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_filename, verbose=False)
    return result