"""Port en caisse les paiements valides qui n'ont pas d'entree.

Quand aucune caisse n'etait ouverte, la validation reussissait sans
ecriture : le paiement restait VALIDE et l'argent n'apparaitait nulle
part dans la caisse. Une fois le comportement corrige, ces paiements
anterieurs restent orphelins — leur statut ne repasse plus par
ENREGISTRE, donc la validation ne peut pas etre rejouee.

Cette commande rattrape les arrears. Elle est sans effet sur un
paiement deja porte, et n'ouvre une caisse que si un versement a
lieu : consulter ne doit pas creer de caisse.

Usage :
    python manage.py porter_paiements_en_caisse --dry-run
    python manage.py porter_paiements_en_caisse
"""
from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from Gestion.models import (
    Caisse, EntreeCaisse, Paiement, Utilisateur,
)


class Command(BaseCommand):
    help = "Port en caisse les paiements valides sans entree de caisse."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait porte sans ecrire.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        deja_portes = EntreeCaisse.objects.exclude(
            paiement=None
        ).values_list("paiement_id", flat=True)

        orphelins = list(
            Paiement.objects
            .filter(statut=Paiement.VALIDE)
            .exclude(id__in=deja_portes)
            .select_related(
                "inscription", "inscription__eleve",
                "tranche", "tranche__frais", "valide_par",
            )
            .order_by("date_paiement")
        )

        if not orphelins:
            self.stdout.write(self.style.SUCCESS(
                "Aucun paiement valide sans entree de caisse."
            ))
            return

        total = sum((p.montant for p in orphelins), Decimal("0"))

        self.stdout.write(self.style.WARNING(
            f"{len(orphelins)} paiement(s) valide(s) hors caisse, "
            f"total {total}."
        ))

        for paiement in orphelins:
            self.stdout.write(
                f"  #{paiement.id} {paiement.inscription.eleve}"
                f" | tranche n° {paiement.tranche.numero}"
                f" | {paiement.montant}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Simulation : aucune ecriture."
            ))
            return

        # L'utilisateur qui a valide le paiement est l'auteur le plus
        # coherent de l'entree ; a defaut, le premier compte actif.
        auteur = (
            orphelins[-1].valide_par
            or Utilisateur.objects.filter(actif=True).order_by("id").first()
        )

        if auteur is None:
            self.stdout.write(self.style.ERROR(
                "Aucun utilisateur actif : entree impossible."
            ))
            return

        with transaction.atomic():
            caisse = (
                Caisse.objects
                .filter(statut=Caisse.OUVERTE)
                .order_by("-id")
                .first()
            )

            if caisse is None:
                maintenant = timezone.localtime()
                caisse = Caisse.objects.create(
                    libelle=f"Caisse du {maintenant:%d/%m/%Y %H:%M}",
                    heure_ouverture=maintenant.time().replace(
                        microsecond=0
                    ),
                    # Caisse.clean exige une fermeture posterieure.
                    heure_fermeture=time(23, 59),
                    statut=Caisse.OUVERTE,
                )
                self.stdout.write(
                    f"Caisse « {caisse.libelle} » ouverte."
                )

            for paiement in orphelins:
                EntreeCaisse.objects.create(
                    caisse=caisse,
                    paiement=paiement,
                    montant=paiement.montant,
                    enregistre_par=auteur,
                )
                self.stdout.write(
                    f"  #{paiement.id} porte sur « {caisse.libelle} »."
                )

        self.stdout.write(self.style.SUCCESS(
            f"{len(orphelins)} entree(s) creee(s) sur "
            f"« {caisse.libelle} »."
        ))