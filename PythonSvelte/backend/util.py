def get_file_extension(filename):
	return filename.rsplit(".", 1)[1].lower()

def allowed_file(filename, allowed_extensions):
	return '.' in filename and get_file_extension(filename) in allowed_extensions

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{int(hours)}:{int(minutes):02}:{seconds:04.1f}"
    elif minutes > 0:
        return f"{int(minutes)}:{seconds:04.1f}"
    else:
        return f"{seconds:.1f}"