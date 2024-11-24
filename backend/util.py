import os

def get_file_extension(filename: str)-> str:
	return filename.rsplit(".", 1)[1].lower()

def allowed_file(filename: str, allowed_extensions: list[str])-> bool:
	return '.' in filename and get_file_extension(filename) in allowed_extensions

def format_time(seconds: float)-> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{int(hours)}:{int(minutes):02}:{seconds:04.1f}"
    elif minutes > 0:
        return f"{int(minutes)}:{seconds:04.1f}"
    else:
        return f"{seconds:.1f}"
    
def full_clean(d: str) -> None:
	for filename in os.listdir(d):
		filepath = os.path.join(d, filename)
		os.remove(filepath)
            
def make_folder(d: str) -> None:
    if not os.path.exists(d):
        os.makedirs(d)