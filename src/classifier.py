import json
import anthropic
from ingestion import FileRecord


class KeyWordClassifier:

    def __init__(self, record: FileRecord):
        self.file = record
        self.keywords = {
            "Documents_identite": ["carte_identite", "cni", "identite", "passeport", "permis"],
            "Maintenance": ["maintenance", "batterie"],
            "Exports_donnees": ["export", "transaction"],
            "Contrats": ["contrat", "convention", "accord"],
            "Factures": ["facture", "paiement", "recu"],
            "Rapports": ["rapport", "bilan", "synthese", "analyse", "etude", "compte_rendu"],
            "Photos": ["photo", "image", "img", "screenshot", "capture_ecran"],
            "Autre": ["planning", "bon_de_commande"]
        }

    def classify(self):
        for categorie, mots in self.keywords.items():
            for mot in mots:
                if mot in self.file.name.lower():
                    self.file.categorie = categorie
                    self.file.confiance = 1.0
                    return self.file
        return None


SYSTEM_PROMPT = """Tu es un système de classification de fichiers pour FANGA, 
une plateforme ivoirienne de mobilité électrique.

Tu dois classer chaque fichier dans exactement une de ces catégories :
- Contrats : contrats de vente, accords partenaires, conventions
- Factures : factures, bons de paiement, reçus
- Photos : images de stations, de motos, de terrain
- Rapports : rapports mensuels, bilans, synthèses
- Exports_donnees : fichiers CSV, exports de transactions, données brutes
- Documents_identite : cartes d'identité, passeports, justificatifs
- Maintenance : rapports de maintenance, fiches techniques, interventions
- Autre : tout ce qui ne correspond à aucune catégorie ci-dessus

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après :
{"categorie": "...", "confiance": 0.00, "description_courte": "..."}

La description_courte : minuscules, tirets à la place des espaces, 4 mots max.
Si tu hésites, baisse la confiance plutôt que de deviner."""


class ClaudeClassifier:

    def __init__(self, api_key: str, threshold: float = 0.70):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.threshold = threshold

    def _build_user_prompt(self, record: FileRecord) -> str:
        contenu = ""
        try:
            with open(record.path, "r", encoding="utf-8") as f:
                contenu = f.read(1000) 
        except Exception:
            contenu = "Contenu non lisible"
        return f"""Fichier à classifier :
        - Nom original : {record.name}
        - Extension : {record.extension}
        - Taille : {record.size} octets
        - Contenu : {contenu}"""

    def _parse_response(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
            raise

    def classify(self, record: FileRecord) -> FileRecord:
        try:
            print("CLAUDE EN COURRRRRRS")
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": self._build_user_prompt(record)
                }]
            )
            print("Claude est sorti")
            print(response.content[0].text)
            result = self._parse_response(response.content[0].text)

            record.categorie = result["categorie"]
            record.confiance = float(result["confiance"])
            record.description_courte = result["description_courte"]

        except Exception as e:
            record.categorie = "A_verifier"
            record.confiance = 0.0
            record.description_courte = "erreur-classification"
            record.erreur = str(e)
            print(f"ERREUR CLAUDE : {e}") 

        return record