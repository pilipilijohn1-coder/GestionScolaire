from django.core.management.base import BaseCommand
from django.db import transaction

from Gestion.models import (
    DomaineEnseignement,
    Matiere,
    Niveau,
    PonderationMatiere,
)


class Command(BaseCommand):

    help = (
        "Initialise les matières et pondérations "
        "officielles des 7e et 8e années."
    )

    @transaction.atomic
    def handle(self, *args, **options):

        domaines = [
            {
                "code": "MATHEMATIQUES",
                "libelle": "Sous-domaine des mathématiques",
                "ordre": 1,
            },
            {
                "code": "SVT",
                "libelle": (
                    "Sous-domaine des sciences de la vie "
                    "et de la terre (SVT)"
                ),
                "ordre": 2,
            },
            {
                "code": "SPT_TIC",
                "libelle": (
                    "Sous-domaine des sciences physiques, "
                    "technologie et TIC"
                ),
                "ordre": 3,
            },
            {
                "code": "LANGUES",
                "libelle": "Domaine des langues",
                "ordre": 4,
            },
            {
                "code": "UNIVERS_SOCIAL",
                "libelle": (
                    "Domaine de l'univers social "
                    "et environnement"
                ),
                "ordre": 5,
            },
            {
                "code": "ARTS",
                "libelle": "Domaine des arts",
                "ordre": 6,
            },
            {
                "code": "DEVELOPPEMENT_PERSONNEL",
                "libelle": "Domaine du développement personnel",
                "ordre": 7,
            },
        ]

        domaines_crees = {}

        for data in domaines:

            domaine, _ = DomaineEnseignement.objects.update_or_create(
                code=data["code"],
                defaults={
                    "libelle": data["libelle"],
                    "ordre": data["ordre"],
                    "actif": True,
                }
            )

            domaines_crees[data["code"]] = domaine

        matieres = [

            # =========================
            # MATHEMATIQUES
            # =========================

            {
                "code": "ALGEBRE",
                "libelle": "Algèbre",
                "domaine": "MATHEMATIQUES",
                "tj": 40,
                "examen": 80,
            },

            {
                "code": "ARITHMETIQUE",
                "libelle": "Arithmétique",
                "domaine": "MATHEMATIQUES",
                "tj": 10,
                "examen": 20,
            },

            {
                "code": "GEOMETRIE",
                "libelle": "Géométrie",
                "domaine": "MATHEMATIQUES",
                "tj": 20,
                "examen": 40,
            },

            {
                "code": "STATISTIQUE",
                "libelle": "Statistique",
                "domaine": "MATHEMATIQUES",
                "tj": 10,
                "examen": 20,
            },

            # =========================
            # SVT
            # =========================

            {
                "code": "ANATOMIE",
                "libelle": "Anatomie",
                "domaine": "SVT",
                "tj": 10,
                "examen": 20,
            },

            {
                "code": "BOTANIQUE",
                "libelle": "Botanique",
                "domaine": "SVT",
                "tj": 10,
                "examen": 20,
            },

            {
                "code": "ZOOLOGIE",
                "libelle": "Zoologie",
                "domaine": "SVT",
                "tj": 10,
                "examen": 20,
            },

            # =========================
            # SCIENCES / TECHNOLOGIE / TIC
            # =========================

            {
                "code": "SCIENCES_PHYSIQUES",
                "libelle": "Sciences physiques",
                "domaine": "SPT_TIC",
                "tj": 10,
                "examen": 20,
            },

            {
                "code": "TECHNOLOGIE",
                "libelle": "Technologie",
                "domaine": "SPT_TIC",
                "tj": 10,
                "examen": 20,
            },

            {
                "code": "TIC",
                "libelle": (
                    "Techniques d'information "
                    "et de communication (TIC)"
                ),
                "domaine": "SPT_TIC",
                "tj": 10,
                "examen": 20,
            },

            # =========================
            # LANGUES
            # =========================

            {
                "code": "ANGLAIS",
                "libelle": "Anglais",
                "domaine": "LANGUES",
                "tj": 30,
                "examen": 60,
            },

            {
                "code": "FRANCAIS",
                "libelle": "Français",
                "domaine": "LANGUES",
                "tj": 70,
                "examen": 140,
            },

            # =========================
            # UNIVERS SOCIAL
            # =========================

            {
                "code": "EDUCATION_VIE",
                "libelle": "Éducation à la vie",
                "domaine": "UNIVERS_SOCIAL",
                "tj": 20,
                "examen": 40,
            },

            {
                "code": "EDUCATION_CIVIQUE",
                "libelle": "Éducation civique et morale",
                "domaine": "UNIVERS_SOCIAL",
                "tj": 20,
                "examen": 40,
            },

            {
                "code": "GEOGRAPHIE",
                "libelle": "Géographie",
                "domaine": "UNIVERS_SOCIAL",
                "tj": 20,
                "examen": 40,
            },

            {
                "code": "HISTOIRE",
                "libelle": "Histoire",
                "domaine": "UNIVERS_SOCIAL",
                "tj": 20,
                "examen": 40,
            },

            # =========================
            # ARTS
            # =========================

            {
                "code": "DESSIN",
                "libelle": "Dessin",
                "domaine": "ARTS",
                "tj": 20,
                "examen": 40,
            },

            {
                "code": "MUSIQUE",
                "libelle": "Musique",
                "domaine": "ARTS",
                "tj": 20,
                "examen": 40,
            },

            # =========================
            # DEVELOPPEMENT PERSONNEL
            # =========================

            {
                "code": "EDUCATION_PHYSIQUE",
                "libelle": "Éducation physique",
                "domaine": "DEVELOPPEMENT_PERSONNEL",
                "tj": 20,
                "examen": 40,
            },
        ]

        # -------------------------------------
        # Création des matières
        # -------------------------------------

        matieres_creees = {}

        for data in matieres:

            matiere, _ = Matiere.objects.update_or_create(
                code=data["code"],
                defaults={
                    "libelle": data["libelle"],
                    "domaine": domaines_crees[data["domaine"]],
                    "actif": True,
                }
            )

            matieres_creees[data["code"]] = matiere

        # -------------------------------------
        # Niveaux 7e et 8e
        # -------------------------------------

        niveaux = Niveau.objects.filter(
            libelle__in=[
                "7ème",
                "8ème",
                "7e",
                "8e",
                "7ème année",
                "8ème année",
            ]
        )

        if not niveaux.exists():

            self.stdout.write(
                self.style.ERROR(
                    "Aucun niveau 7e ou 8e trouvé."
                )
            )

            self.stdout.write(
                "Crée d'abord les niveaux 7e et 8e."
            )

            return

        # -------------------------------------
        # Création des pondérations
        # -------------------------------------

        nombre_ponderations = 0

        for niveau in niveaux:

            for data in matieres:

                tj = data["tj"]
                examen = data["examen"]

                total = (
                    (2 * tj)
                    + examen
                )

                PonderationMatiere.objects.update_or_create(
                    niveau=niveau,
                    matiere=matieres_creees[data["code"]],
                    defaults={
                        "travaux_journaliers_max": tj,
                        "examen_max": examen,
                        "total_semestre_max": total,
                        "actif": True,
                    }
                )

                nombre_ponderations += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Initialisation terminée avec succès."
            )
        )

        self.stdout.write(
            f"Domaines : {len(domaines_crees)}"
        )

        self.stdout.write(
            f"Matières : {len(matieres_creees)}"
        )

        self.stdout.write(
            f"Pondérations créées/mises à jour : "
            f"{nombre_ponderations}"
        )
