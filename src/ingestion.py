class FileRecord:
    """Représente le fichier en cours de traitement"""
    def __init__(self, file_path: str):
        self.path = file_path
        self.name = file_path.split("/")[-1]
        self.size = os.path.getsize(file_path)
        self.date = os.path.getmtime(file_path)
