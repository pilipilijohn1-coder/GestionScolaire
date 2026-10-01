# Gestion Scolaire

Application Django de gestion scolaire : élèves, classes, enseignants,
cours, emploi du temps, notes, bulletins et finances.

## Prérequis

- Python 3.13
- SQL Server + **ODBC Driver 17 for SQL Server**

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Les secrets ne sont **pas** versionnés. Deux possibilités :

1. Créer un fichier `GestionScolaire/local_settings.py` (ignoré par git) :

   ```python
   SECRET_KEY = "..."
   DATABASES = {
       "default": {
           "ENGINE": "mssql",
           "NAME": "Gestion_Ecole",
           "USER": "...",
           "PASSWORD": "...",
           "HOST": "...",
           "PORT": "",
           "OPTIONS": {"driver": "ODBC Driver 17 for SQL Server"},
       }
   }
   ```

2. Ou définir les variables d'environnement listées dans `.env.example`.

## Commandes de gestion

| Commande | Rôle |
|---|---|
| `python manage.py migrate` | Applique les migrations |
| `python manage.py initialiser_bulletin` | **Source de vérité des cours** : domaines, matières, niveaux, sections, pondérations et modèles de bulletins |
| `python manage.py initialiser_permissions` | Crée les rôles et permissions |

`initialiser_bulletin` peut être relancé sans créer de doublons.

## Conventions importantes

- **Les cours d'une classe** proviennent de `PonderationMatiere` filtré sur
  le niveau et la section de la classe. `AffectationMatiere` n'ajoute aucune
  ligne : elle ne fait qu'annoter un cours déjà présent avec son volume horaire.
- Un cours absent d'`AffectationMatiere` reste donc visible.
- La base contient deux générations de pondérations pour les niveaux
  spécialisés (lignes sans `section` et lignes par `section`) : le regroupement
  se fait par matière, en privilégiant la section de la classe, afin de ne
  jamais afficher un cours en double.
- `ConfigurationHoraire.verrouillee` est **définitif** : une fois l'année
  validée, ses créneaux ne peuvent plus être régénérés.

## Structure

```
GestionScolaire/     projet Django (settings, urls, wsgi)
Gestion/             application principale
  models.py          modèles (Eleve, Classe, Affectation, Horaire, Bulletin...)
  views.py           vues
  forms.py           formulaires
  permissions/       permissions et décorateurs
  service/           logique métier (bulletin, finance, notification...)
  management/commands/  initialiser_bulletin, initialiser_permissions
  templatetags/      filtres et tags personnalisés
templates/           templates HTML
media/               fichiers envoyés (photos) — non versionné
```