# Rapport — Pipeline de Données Fashion AI

**Projet :** Fashion AI MVP  
**Équipe :** fashion-ai-team  
**Date :** Mars 2026

---

## 1. Architecture du Pipeline

### 1.1 Vue d'ensemble

Le pipeline Fashion AI est une chaîne de traitement de données orchestrée par **Apache Airflow**, conteneurisée avec **Docker Compose**. Son objectif est d'ingérer un catalogue d'images de mode, de les transformer via **Apache Spark**, puis de les indexer sous forme de vecteurs dans **Qdrant** pour permettre la recherche par similarité visuelle dans l'application Streamlit.

### 1.2 Services Docker

L'infrastructure est composée de **7 services** déployés via `docker-compose.yml` :

| Service | Image / Build | Port | Rôle |
|---------|--------------|------|------|
| **postgres** | `postgres:15` | — | Base de métadonnées Airflow (executor, DAG runs, XCom) |
| **airflow-webserver** | `airflow/Dockerfile` | 8080 | Interface web Airflow (monitoring, déclenchement) |
| **airflow-scheduler** | `airflow/Dockerfile` | — | Planification et exécution des tâches du DAG |
| **airflow-init** | `airflow/Dockerfile` | — | Initialisation de la base Airflow + création utilisateur admin |
| **qdrant** | `qdrant/qdrant:latest` | 6333 | Base de données vectorielle (stockage et recherche d'embeddings) |
| **redis** | `redis:7-alpine` | 6379 | File de messages pour le traitement d'images en temps réel |
| **streamlit** | `Dockerfile` (Python 3.11-slim) | 8501 | Application web utilisateur (recherche, favoris, analytics) |

### 1.3 Schéma d'architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                          │
│                                                             │
│  ┌──────────┐    ┌───────────────┐    ┌───────────────┐    │
│  │ Postgres │◄───│   Airflow     │───►│    Qdrant     │    │
│  │  (meta)  │    │ Scheduler +   │    │  (vecteurs)   │    │
│  └──────────┘    │ Webserver     │    └───────┬───────┘    │
│                  └───────┬───────┘            │            │
│                          │                    │            │
│                  ┌───────▼───────┐    ┌───────▼───────┐    │
│                  │  Spark (local)│    │   Streamlit   │    │
│                  │  transform    │    │   (app web)   │    │
│                  └───────────────┘    └───────┬───────┘    │
│                                              │            │
│                                      ┌───────▼───────┐    │
│                                      │    Redis      │    │
│                                      │   (queue)     │    │
│                                      └───────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Images Docker

Le projet utilise **deux Dockerfiles distincts** :

- **`Dockerfile`** (racine) — Image légère `python:3.11-slim` pour le service Streamlit uniquement. Installe les dépendances applicatives (`requirements.txt`) et copie le code source (`src/`) et les données (`Data/`).

- **`airflow/Dockerfile`** — Étend `apache/airflow:2.9.2` avec Java (pour Spark), PySpark, le modèle CLIP (`sentence-transformers`), `qdrant-client` et Pillow. Utilisé par tous les services Airflow.

---

## 2. Fonctionnement du DAG

### 2.1 Identité du DAG

| Paramètre | Valeur |
|-----------|--------|
| `dag_id` | `fashion_pipeline_v2` |
| `schedule_interval` | `0 2 * * *` (tous les jours à 2h du matin) |
| `start_date` | 1er janvier 2024 |
| `catchup` | `False` (pas de rattrapage des exécutions passées) |
| `max_active_runs` | 1 (une seule exécution simultanée) |
| `retries` | 2 tentatives par tâche, délai de 5 minutes |
| `execution_timeout` | 2 heures maximum par tâche |

### 2.2 Configuration dynamique

Le DAG utilise les **Airflow Variables** pour paramétrer les chemins et connexions, avec des valeurs par défaut :

| Variable | Défaut | Description |
|----------|--------|-------------|
| `fashion_catalog_dir` | `/opt/airflow/Data/catalog` | Dossier source des images |
| `fashion_processed_dir` | `/opt/airflow/Data/processed` | Dossier de sortie Spark |
| `fashion_reports_dir` | `/opt/airflow/Data/reports` | Dossier des rapports JSON |
| `spark_master` | `local[*]` | URL du cluster Spark |
| `spark_driver_memory` | `2g` | Mémoire allouée au driver Spark |
| `qdrant_host` | `qdrant` | Hôte du service Qdrant |
| `qdrant_port` | `6333` | Port du service Qdrant |

### 2.3 Description des tâches

Le DAG comporte **10 tâches** organisées en **2 Task Groups** :

#### Phase 1 — Initialisation
- **`start`** : Tâche vide (`EmptyOperator`) marquant le début du pipeline.
- **`setup_environment`** : Crée les répertoires nécessaires (`catalog`, `processed`, `reports`) via `os.makedirs`.
- **`check_spark`** : Vérifie que `spark-submit` est installé et fonctionnel en exécutant `spark-submit --version`.

#### Phase 2 — Ingestion des données (TaskGroup `data_ingestion`)
- **`validate_catalog`** : Vérifie l'existence et les permissions du dossier catalogue.
- **`ingest_images`** : Parcourt le catalogue, extrait les métadonnées de chaque image (dimensions, taille, hash MD5 pour dédoublonnage), pousse le tout dans XCom et sauvegarde en JSON.

#### Phase 3 — Transformation Spark
- **`create_spark_script`** : Génère dynamiquement un script PySpark à partir du chemin du fichier de métadonnées récupéré via XCom.
- **`spark_transform`** (`BashOperator`) : Exécute le script Spark qui filtre les images invalides (< 224px), calcule le ratio d'aspect et les mégapixels, puis sauvegarde en JSON.

#### Phase 4 — Indexation vectorielle (TaskGroup `vector_indexing`)
- **`check_qdrant`** : Vérifie la connectivité avec le service Qdrant et liste les collections existantes.
- **`index_vectors`** : Encode chaque image avec le modèle **CLIP (clip-ViT-B-32)** en vecteurs de dimension 512, puis les indexe dans Qdrant par lots de 10 avec gestion d'erreurs unitaire.

#### Phase 5 — Validation et rapport
- **`validate_and_report`** : Collecte les métriques (images détectées, indexées, erreurs), calcule le taux de succès, génère un rapport JSON horodaté et applique une porte de qualité (seuil minimum : 80 %).

---

## 3. Dépendances entre les tâches

### 3.1 Graphe de dépendances

```
start ──┬── setup_environment ──┐
        │                       ├── data_ingestion ──── create_spark_script ──── spark_transform ──── vector_indexing ──── validate_and_report ──── end
        └── check_spark ────────┘       │                                                                  │
                                        │                                                                  │
                                  validate_catalog                                                   check_qdrant
                                        │                                                                  │
                                  ingest_images                                                      index_vectors
```

### 3.2 Tableau des dépendances

| Tâche | Dépend de | Type |
|-------|-----------|------|
| `start` | — | Début |
| `setup_environment` | `start` | Parallèle avec `check_spark` |
| `check_spark` | `start` | Parallèle avec `setup_environment` |
| `data_ingestion.validate_catalog` | `setup_environment` ET `check_spark` | Attend les deux |
| `data_ingestion.ingest_images` | `validate_catalog` | Séquentiel dans le groupe |
| `create_spark_script` | `data_ingestion` (groupe entier) | XCom : `metadata_file` |
| `spark_transform` | `create_spark_script` | Script généré |
| `vector_indexing.check_qdrant` | `spark_transform` | Séquentiel |
| `vector_indexing.index_vectors` | `check_qdrant` | XCom : `images_metadata` |
| `validate_and_report` | `vector_indexing` (groupe entier) | XCom : `indexed_count`, `indexing_errors` |
| `end` | `validate_and_report` | Fin (`trigger_rule=all_done`) |

### 3.3 Communication inter-tâches (XCom)

Les tâches échangent des données via le mécanisme **XCom** d'Airflow :

| Clé XCom | Producteur | Consommateur | Contenu |
|----------|-----------|-------------|---------|
| `images_metadata` | `ingest_images` | `index_vectors` | Liste de dictionnaires (path, filename, size, hash, dimensions) |
| `image_count` | `ingest_images` | `validate_and_report` | Nombre total d'images détectées |
| `metadata_file` | `ingest_images` | `create_spark_script` | Chemin du fichier JSON de métadonnées |
| `indexed_count` | `index_vectors` | `validate_and_report` | Nombre de vecteurs indexés avec succès |
| `indexing_errors` | `index_vectors` | `validate_and_report` | Liste des erreurs d'encodage |

---

## 4. Choix techniques

### 4.1 Orchestration — Apache Airflow 2.9.2

**Pourquoi Airflow ?**
- Gestion native des dépendances entre tâches avec un graphe orienté acyclique (DAG).
- Interface web intégrée pour le monitoring, la consultation des logs et le déclenchement manuel.
- Mécanisme de **retry** automatique (2 tentatives, délai de 5 min) pour la tolérance aux pannes.
- Communication inter-tâches via **XCom** sans infrastructure supplémentaire.
- **Task Groups** pour organiser visuellement les tâches par phase logique.

**Executor choisi :** `LocalExecutor` — exécution parallèle des tâches sur un seul nœud via PostgreSQL, suffisant pour ce MVP sans la complexité de Celery ou Kubernetes.

### 4.2 Traitement distribué — Apache Spark 3.5 (PySpark)

**Pourquoi Spark ?**
- Capacité de traitement de gros volumes d'images grâce au parallélisme natif.
- Opérations de filtrage, enrichissement et dédoublonnage exprimées de manière déclarative via l'API DataFrame.
- Mode `local[*]` pour le développement, extensible vers un cluster en production.

**Transformations appliquées :**
- Filtrage des images corrompues (`size_bytes > 0`) et trop petites (`width >= 224, height >= 224`).
- Enrichissement : calcul du ratio d'aspect (`width / height`) et des mégapixels.
- Export en JSON partitionné avec `coalesce(1)` pour un fichier unique.

### 4.3 Base vectorielle — Qdrant

**Pourquoi Qdrant ?**
- Base de données spécialisée pour la recherche par similarité vectorielle (ANN — Approximate Nearest Neighbors).
- Supporte la distance **cosinus**, adaptée aux embeddings normalisés du modèle CLIP.
- API Python simple (`qdrant-client`) pour l'indexation et la recherche.
- Stockage persistant via volume Docker (`qdrant_storage`).

**Dimensionnement :** Vecteurs de dimension **512** (sortie de CLIP ViT-B/32), indexation par lots de **10** avec gestion d'erreurs unitaire.

### 4.4 Modèle d'embeddings — CLIP (ViT-B/32)

**Pourquoi CLIP ?**
- Modèle multimodal (texte + image) permettant la recherche cross-modale : un utilisateur peut chercher par texte ("robe rouge") et retrouver des images correspondantes.
- Pré-entraîné par OpenAI, utilisé via `sentence-transformers` sans fine-tuning.
- Dimension compacte (512) offrant un bon compromis entre précision et performance.

### 4.5 Conteneurisation — Docker Compose

**Pourquoi Docker ?**
- Environnement reproductible : chaque développeur et chaque déploiement utilise les mêmes versions.
- Isolation des services : Airflow, Qdrant, Redis et Streamlit fonctionnent dans des conteneurs séparés.
- Deux images distinctes optimisées :
  - **Airflow** (`airflow/Dockerfile`) : image lourde avec Java + Spark + modèle CLIP.
  - **Streamlit** (`Dockerfile`) : image légère `python:3.11-slim` pour l'application web.

### 4.6 Porte de qualité (Quality Gate)

Le pipeline intègre un mécanisme de validation automatique :
- **Seuil minimum** : 80 % des images doivent être indexées avec succès.
- **Détection de skip** : si l'indexation n'a pas été exécutée (échec en amont), le pipeline le signale explicitement.
- **Rapport JSON** : un rapport horodaté est généré à chaque exécution avec les métriques, les erreurs et le résultat des contrôles qualité.

### 4.7 Gestion des erreurs

| Mécanisme | Détail |
|-----------|--------|
| Retries automatiques | 2 tentatives par tâche, délai de 5 minutes |
| Timeout | 2 heures maximum par tâche |
| Erreurs unitaires | L'échec d'encodage d'une image n'arrête pas le lot |
| Trigger rule `all_done` | `validate_and_report` s'exécute même si des tâches échouent, pour toujours produire un rapport |
| Health check Qdrant | Vérification de la connectivité avant de commencer l'indexation |

---

## Annexe — Arborescence du projet

```
FASHION_AI_MVP/
├── airflow/
│   ├── Dockerfile              # Image Airflow + Spark + CLIP
│   ├── dags/
│   │   └── fashion_pipeline_dag.py   # DAG principal (10 tâches)
│   └── logs/                   # Logs Airflow (volume Docker)
├── Data/
│   └── catalog/                # Images source du catalogue
├── spark_jobs/
│   └── transform_catalog.py    # Script Spark autonome
├── src/
│   ├── app.py                  # Application Streamlit
│   ├── batch_indexer.py        # Indexation offline (hors pipeline)
│   ├── utile.py                # Utilitaires (Qdrant, CLIP, auth)
│   ├── profile_ai.py           # Gestion des profils utilisateur
│   ├── producer.py             # Producteur Redis (watchdog)
│   └── worker_ia.py            # Worker Redis (encodage temps réel)
├── docker-compose.yml          # Orchestration des 7 services
├── Dockerfile                  # Image Streamlit (python:3.11-slim)
└── requirements.txt            # Dépendances Python
```
