# FANGA — Pipeline de Classification Automatique de Fichiers

> Test technique — Développeur Automatisation IA  
> Candidat : `[Akandé Philippe ABIODOUN]`  
> Repository : `[https://github.com/vrmelox/fanga_pipeline]`


## Setup et exécution

### Prérequis

- Python 3.10+
- Une clé API Anthropic

### Installation

```bash
git clone [LIEN_GITHUB]
cd fanga-pipeline
pip install -r requirements.txt
```

### Configuration

Créer un fichier `.env` à la racine :

```env
API_KEY=sk-ant-...
```

### Préparer les fichiers de test

Placer les fichiers suivants dans le dossier `fanga_inbox/` à la racine du projet :

```
fanga_inbox/
├── contrat_aissata_kone_2024.pdf
├── facture_station_cocody_mars.pdf
├── photo_station_plateau_01.jpg
├── rapport_mensuel_conducteurs.xlsx
├── export_transactions_fevrier.csv
├── carte_identite_yacouba.png
├── maintenance_batterie_ST-002.docx
├── planning_equipe_avril.pdf
├── bon_de_commande_motos.pdf
└── screenshot_app_bug.png
```

### Exécution

```bash
cd src
python3 main.py
```

### Résultat attendu

```
fanga_organised/
├── Contrats/
├── Factures/
├── Photos/
├── Rapports/
├── Exports_donnees/
├── Documents_identite/
├── Maintenance/
├── Autre/
├── A_verifier/
└── rapport_traitement.json
```

---

## Architecture

Le pipeline est découpé en 4 classes indépendantes orchestrées par `Pipeline`. Chaque classe a une responsabilité unique et peut être modifiée sans impacter les autres.

```
fanga-pipeline/
├── fanga_inbox/           # Dossier d'entrée
├── fanga_organised/       # Dossier de sortie généré automatiquement
└── src/
    ├── main.py            # Point d'entrée
    ├── pipeline.py        # Classe Pipeline — orchestrateur principal
    ├── ingestion.py       # Classe FileRecord — objet de données
    ├── classifier.py      # Classes KeyWordClassifier + ClaudeClassifier
```

### Flux de traitement

```
fanga_inbox/
     │
     ▼
1. LISTING
Lecture du dossier → création d'un FileRecord par fichier
(nom, extension, taille, date, chemin)
     │
     ▼
2. ANALYSE
KeyWordClassifier cherche un mot-clé dans le nom du fichier
  │
  ├── Match trouvé → catégorie assignée, confiance = 1.0, pas d'appel API
  │
  └── Pas de match → ClaudeClassifier
                      Envoi du nom + extension + contenu extrait à Claude
                      Réponse : { categorie, confiance, description_courte }
     │
     ▼
3. CLASSIFICATION
  confiance ≥ 0.70 → fanga_organised/{categorie}/
  confiance < 0.70 → fanga_organised/A_verifier/
  Renommage : YYYY-MM-DD_{categorie}_{nom_nettoye}.{ext}
     │
     ▼
4. RAPPORT
rapport_traitement.json généré à partir de tous les résultats
```


## Stratégie de classification

### Double stratégie : mot-clé d'abord, Claude en dernier recours

La classification repose sur deux mécanismes complémentaires. L'objectif est de réduire les appels API(réduire les coûts) tout en garantissant une classification correcte pour les cas ambigus.

**Étape 1 — Classification par mot-clé** : si le nom du fichier contient un mot-clé métier reconnu, le fichier est classifié immédiatement avec une confiance de 1.0. Cette étape couvre la majorité des cas dans un contexte opérationnel où les fichiers suivent des conventions de nommage.

La table de priorité est ordonnée du plus spécifique au plus générique — `Maintenance` prime sur `Rapports` par exemple — pour éviter les ambiguïtés :

```
Documents_identite : carte_identite, cni, identite, passeport, permis
Maintenance        : maintenance, batterie
Exports_donnees    : export, transaction
Contrats           : contrat, convention, accord
Factures           : facture, paiement, recu
Rapports           : rapport, bilan, synthese, analyse, etude, compte_rendu
Photos             : photo, image, img, screenshot, capture_ecran
Autre              : planning, bon_de_commande
```

**Étape 2 — Classification par Claude** : si aucun mot-clé ne matche, le contenu du fichier est extrait et envoyé à Claude avec un prompt contraint. La réponse est un JSON :

```json
{"categorie": "Contrats", "confiance": 0.94, "description_courte": "aissata-kone"}
```

Le prompt demande à Claude de baisser le score de confiance en cas de doute plutôt que de deviner avec une fausse certitude. Tout fichier sous 0.70 de confiance est automatiquement routé vers `A_verifier` pour revue humaine.

### Renommage normalisé

Chaque fichier est renommé selon le format :

```
YYYY-MM-DD_{categorie}_{nom_original_nettoye}.{ext}
```

Le nom original est nettoyé en minuscules avec les underscores et espaces remplacés par des tirets. Ce format garantit un tri chronologique naturel et une lisibilité immédiate.

---

## Améliorations envisagées

**Extraction de contenu enrichie** : le pipeline lit actuellement le contenu texte brut des fichiers. Une évolution serait d'ajouter des extracteurs dédiés par type : `pypdf2` pour les PDF, `python-docx` pour les DOCX, lecture des headers pour les CSV, et analyse visuelle via une API de reconnaissance d'image.

**Seuils de confiance par catégorie** : certaines catégories sont naturellement plus ambiguës que d'autres. Affiner le seuil par catégorie plutôt qu'un seuil global unique concentrerait l'attention humaine là où le risque d'erreur est réellement élevé.

**Détection de doublons** : Actuellement, je ne gère pas les doublons. Mais on peut faire ça avec un hash du contenu de chaque fichier pour détecter des fichiers identiques renommés différemment avant traitement.

**Mode dry-run** : une option `--dry-run` permettrait de simuler le pipeline sans déplacer aucun fichier, utile pour valider la classification avant de l'appliquer.

**Tests unitaires** : tests sur les extracteurs, sur le parsing de la réponse Claude en cas de JSON malformé, et sur la logique de renommage.

**Notifications** : un webhook Slack ou un email récapitulatif à la fin du pipeline pour les équipes opérationnelles, avec le résumé du rapport et la liste des fichiers à vérifier.

---

## QUESTION FINALE

### Comment faire évoluer la solution pour des milliers de fichiers par jour, garantir la fiabilité, et intégrer une boucle de correction humaine ?

#### Passage à l'échelle

Le pipeline actuel est séquentiel : un fichier à la fois. Pour un volume important provenant de dizaines d'agences, deux évolutions sont nécessaires.

La première est le traitement parallèle : les fichiers peuvent être traités en parallèle dès lors que chaque unité de traitement est indépendante, ce qui est le cas ici. Un pool de workers ou une file de messages permet de distribuer la charge sans changer la logique métier.

La seconde est la normalisation de l'ingestion : les agences partenaires envoient des fichiers avec des conventions de nommage variées et incohérentes. Une couche de pré-traitement standardise les encodages, nettoie les noms de fichiers et détecte les formats non supportés avant même d'entrer dans le pipeline. Cela protège la classification d'entrées imprévisibles.

#### Fiabilité de la classification

La fiabilité ne repose pas uniquement sur le modèle, elle se construit dans le temps grâce à trois mécanismes.

La traçabilité complète : chaque décision de classification est enregistrée avec le fichier source, le contenu extrait transmis à Claude, la catégorie proposée, le score de confiance et l'horodatage. Sans cette trace, il est impossible de diagnostiquer les erreurs récurrentes.

Le monitoring des distributions : si une catégorie représente soudainement 80% des fichiers d'une journée, c'est probablement un signal d'anomalie. Des alertes sur les distributions anormales permettent de détecter les dérives sans attendre les retours humains.

Le seuil adaptatif par catégorie, qui concentre l'attention humaine là où le risque d'erreur est réellement élevé.

#### Boucle de correction humaine

La boucle humaine se décompose en trois niveaux progressifs.

**Niveau 1 — Détection** : déjà en place via le seuil de confiance. Les fichiers ambigus sont isolés automatiquement dans `A_verifier`. C'est la porte d'entrée de la boucle.

**Niveau 2 — Correction** : une interface légère permet à un opérateur de consulter la catégorie proposée par Claude avec sa justification, et de valider ou corriger. La correction est enregistrée avec le fichier source et la prédiction initiale. Ce log de corrections est la matière première de l'amélioration continue.

**Niveau 3 — Apprentissage** : après accumulation d'un volume suffisant de corrections, on analyse les patterns d'erreur. Si Claude confond systématiquement les bons de commande avec des factures, on enrichit le system prompt avec des exemples négatifs explicites pour cette frontière. C'est du prompt engineering itératif — le système s'améliore dans le temps à partir des erreurs réelles, sans intervention sur le code.

Cette boucle transforme chaque erreur en signal utile plutôt qu'en simple anomalie à corriger manuellement.