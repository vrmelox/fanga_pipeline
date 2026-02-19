import os
import shutil
import json
from datetime import datetime
from ingestion import FileRecord
from classifier import KeyWordClassifier, ClaudeClassifier


class Pipeline:
    
    def __init__(self, input_folder: str, output_folder: str, api_key: str, threshold: float = 0.70):
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.threshold = threshold
        self.claude = ClaudeClassifier(api_key=api_key, threshold=threshold)
        self.records = []
    
    def _load_files(self) -> list:
        for filename in os.listdir(self.input_folder):
            file_path = os.path.join(self.input_folder, filename)
            if os.path.isfile(file_path):
                record = FileRecord(file_path)
                self.records.append(record)
        return self.records
    
    def _classify(self, record: FileRecord) -> FileRecord:
        keyword_classifier = KeyWordClassifier(record)
        result = keyword_classifier.classify()
        if result is None:
            record = self.claude.classify(record)
        return record

    def _rename(self, record: FileRecord) -> str:
        # format YYYY-MM-DD
        date = datetime.now().strftime("%Y-%m-%d")
        nom_sans_ext = record.name.rsplit(".", 1)[0]
        nom_nettoye = nom_sans_ext.lower().replace(" ", "-").replace("_", "-")
        # Nom final
        nom_final = f"{date}_{record.categorie}_{nom_nettoye}{record.extension}"
        record.nom_final = nom_final
        return nom_final

    def _move(self, record: FileRecord) -> None:
        if record.confiance < self.threshold:
            sous_dossier = "A_verifier"
        else:
            sous_dossier = record.categorie
        destination_dossier = os.path.join(self.output_folder, sous_dossier)
        os.makedirs(destination_dossier, exist_ok=True)
        destination_finale = os.path.join(destination_dossier, record.nom_final)
        shutil.move(record.path, destination_finale)
        record.path = destination_finale

    def _generate_report(self) -> None:
        classes = {
            "Contrats": 0, "Factures": 0, "Photos": 0,
            "Rapports": 0, "Exports_donnees": 0, "Documents_identite": 0,
            "Maintenance": 0, "Autre": 0, "A_verifier": 0
        }
        
        fichiers = []
        erreurs = []
        
        for record in self.records:
            if record.categorie in classes:
                classes[record.categorie] += 1
            
            entree = {
                "nom_original": record.name,
                "nom_final": record.nom_final,
                "categorie": record.categorie,
                "confiance": record.confiance,
                "statut": "succes" if not hasattr(record, "erreur") else "echec"
            }
            fichiers.append(entree)
            
            if hasattr(record, "erreur"):
                erreurs.append({
                    "nom_original": record.name,
                    "erreur": record.erreur
                })
        
        rapport = {
            "date_execution": datetime.now().isoformat(),
            "total_fichiers": len(self.records),
            "classes": classes,
            "fichiers": fichiers,
            "erreurs": erreurs
        }
        
        # le rapport de la fin
        rapport_path = os.path.join(self.output_folder, "rapport_traitement.json")
        with open(rapport_path, "w", encoding="utf-8") as f:
            json.dump(rapport, f, ensure_ascii=False, indent=2)

    def run(self) -> None:
        print(f"Démarrage du pipeline — dossier : {self.input_folder}")
        
        self._load_files()
        print(f"{len(self.records)} fichiers détectés")
        if len(self.records) == 0:
            print("Aucun fichier à traiter")
            return
        for record in self.records:
            print(f"Traitement : {record.name}")
            self._classify(record)
            self._rename(record)
            self._move(record)
            print(f"→ {record.categorie} (confiance : {record.confiance}) — {record.nom_final}")    
        
        self._generate_report()
        print(f"Pipeline terminé. Rapport généré dans {self.output_folder}")
    
