from django.core.management.base import BaseCommand

from Gestion.models import (
    Affectation,
    AffectationMatiere,
    RepartitionHoraire,
)


class Command(BaseCommand):
    help = (
        "Remet les cours dans les plafonds hebdomadaires : "
        "5 heures et 5 creneaux par cours et par semaine."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--simulation",
            action="store_true",
            help=(
                "Affiche les corrections sans les enregistrer."
            ),
        )
        parser.add_argument(
            "--conserver-creneaux",
            action="store_true",
            help=(
                "Conserve les creneaux excedentaires au lieu de les "
                "retirer. Le volume reste corrige dans tous les cas."
            ),
        )

    def handle(self, *args, **options):
        simulation = options["simulation"]
        conserver = options["conserver_creneaux"]

        if simulation:
            self.stdout.write(self.style.WARNING(
                "SIMULATION : aucune donnee ne sera modifiee."
            ))

        max_heures = AffectationMatiere.HEURES_MAX_PAR_SEMAINE
        max_creneaux = AffectationMatiere.CRENEAUX_MAX

        # =====================================================
        # 1. VOLUMES HORAIRES
        # =====================================================

        volumes_corriges = []

        for affectation_matiere in (
            AffectationMatiere.objects
            .filter(actif=True)
            .select_related("classe", "matiere")
            .order_by("classe__niveau__ordre", "classe__code", "matiere__libelle")
        ):
            if affectation_matiere.heures_par_semaine <= max_heures:
                continue

            volumes_corriges.append({
                "id": affectation_matiere.id,
                "classe": affectation_matiere.classe.libelle,
                "matiere": affectation_matiere.matiere.libelle,
                "avant": affectation_matiere.heures_par_semaine,
                "apres": max_heures,
            })

            if not simulation:
                affectation_matiere.heures_par_semaine = max_heures
                affectation_matiere.save(
                    update_fields=["heures_par_semaine"]
                )

        # =====================================================
        # 2. CRENEAUX EXCEDENTAIRES
        # =====================================================

        creneaux_retires = []

        for affectation in (
            Affectation.objects
            .filter(actif=True)
            .select_related(
                "affectation_matiere",
                "affectation_matiere__classe",
                "affectation_matiere__matiere",
            )
        ):
            repartitions = list(
                RepartitionHoraire.objects
                .filter(affectation=affectation, actif=True)
                .select_related("creneau")
                .order_by("jour", "creneau__ordre")
            )

            if len(repartitions) > max_creneaux:
                excedentaires = repartitions[max_creneaux:]
            else:
                excedentaires = []

            if not excedentaires:
                continue

            libelle_jour = dict(
                RepartitionHoraire.JOUR_CHOICES
            )

            for repartition in excedentaires:
                creneaux_retires.append({
                    "classe": affectation.affectation_matiere.classe.libelle,
                    "matiere": affectation.affectation_matiere.matiere.libelle,
                    "jour": libelle_jour.get(repartition.jour, repartition.jour),
                    "creneau": repartition.creneau.ordre,
                    "heure": (
                        f"{repartition.creneau.heure_debut:%H:%M}"
                        f"-{repartition.creneau.heure_fin:%H:%M}"
                    ),
                })

                if not simulation and not conserver:
                    repartition.delete()

            if conserver and not simulation:
                self.stdout.write(self.style.WARNING(
                    f"  {affectation.affectation_matiere.matiere.libelle} "
                    f"conserve {len(excedentaires)} creneau(x) "
                    f"au-dessus du plafond (execution avec "
                    f"--conserver-creneaux)."
                ))

        # =====================================================
        # 3. COMPTE RENDU
        # =====================================================

        self.stdout.write("")
        self.stdout.write("VOLUMES HORAIRES CORRIGES")
        self.stdout.write("-" * 60)

        if not volumes_corriges:
            self.stdout.write("  Aucun volume au-dessus du plafond.")

        for ligne in volumes_corriges:
            self.stdout.write(
                f"  {ligne['classe']:20} {ligne['matiere']:24} "
                f"{ligne['avant']} h -> {ligne['apres']} h"
            )

        self.stdout.write("")
        self.stdout.write("CRENEAUX RETIRES")
        self.stdout.write("-" * 60)

        if not creneaux_retires:
            self.stdout.write("  Aucun cours au-dessus du plafond.")

        for ligne in creneaux_retires:
            self.stdout.write(
                f"  {ligne['classe']:20} {ligne['matiere']:24} "
                f"{ligne['jour']:10} creneau {ligne['creneau']} "
                f"({ligne['heure']})"
            )

        self.stdout.write("")

        if simulation:
            self.stdout.write(self.style.WARNING(
                "Simulation terminee : aucune ecriture effectuee."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{len(volumes_corriges)} volume(s) et "
                f"{0 if conserver else len(creneaux_retires)} "
                f"creneau(x) corriges."
            ))