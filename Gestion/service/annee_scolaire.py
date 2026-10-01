from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import (
    AnneeScolaire,
    Semestre,
    Periode,
)


@transaction.atomic
def creer_annee_scolaire(
    libelle,
    date_debut,
    date_fin,
    seuil_passage=50,
):
    """
    Crée une nouvelle année scolaire planifiée.
    """

    if date_fin <= date_debut:
        raise ValidationError(
            "La date de fin doit être postérieure à la date de début."
        )

    if AnneeScolaire.objects.filter(libelle=libelle).exists():
        raise ValidationError(
            "Cette année scolaire existe déjà."
        )

    annee = AnneeScolaire.objects.create(
        libelle=libelle,
        date_debut=date_debut,
        date_fin=date_fin,
        seuil_passage=seuil_passage,
        statut=AnneeScolaire.PLANIFIEE,
    )

    # Création obligatoire des deux semestres.
    for numero in (1, 2):
        semestre = Semestre.objects.create(
            annee=annee,
            numero=numero,
            statut=Semestre.OUVERT,
        )

        # Chaque semestre possède exactement deux périodes.
        for numero_periode in (1, 2):
            Periode.objects.create(
                semestre=semestre,
                numero=numero_periode,
                statut=Periode.OUVERTE,
            )

    return annee


@transaction.atomic
def activer_annee_scolaire(annee):
    """
    Active une année scolaire.
    Une seule année doit être active.
    """

    if annee.statut == AnneeScolaire.CLOTUREE:
        raise ValidationError(
            "Une année scolaire clôturée ne peut pas être activée."
        )

    autre = (
        AnneeScolaire.objects
        .filter(statut=AnneeScolaire.ACTIVE)
        .exclude(pk=annee.pk)
        .first()
    )

    if autre:
        raise ValidationError(
            f"L'année {autre.libelle} est déjà active."
        )

    annee.statut = AnneeScolaire.ACTIVE
    annee.save(update_fields=["statut"])

    return annee


@transaction.atomic
def cloturer_annee_scolaire(annee):
    """
    Clôture l'année scolaire.
    """

    if annee.statut != AnneeScolaire.ACTIVE:
        raise ValidationError(
            "Seule une année scolaire active peut être clôturée."
        )

    if annee.date_fin > timezone.localdate():
        raise ValidationError(
            "La date de fin de l'année scolaire n'est pas encore atteinte."
        )

    annee.statut = AnneeScolaire.CLOTUREE
    annee.save(update_fields=["statut"])

    return annee
