import os

class FileRecord:
    """Représente le fichier en cours de traitement"""
    def __init__(self, file_path: str):
        self.path = file_path
        self.name = file_path.split("/")[-1]
        self.extension = "." + self.name.rsplit(".", 1)[-1] if "." in self.name else ""
        self.size = os.path.getsize(file_path)
        self.date = os.path.getmtime(file_path)
        self.categorie = ""
        self.confiance = 0.0
        self.nom_final = ""