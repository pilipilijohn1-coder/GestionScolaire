from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import (
    Eleve,
    AnneeScolaire,
    Classe,
    Inscription,
)


@transaction.atomic
def inscrire_eleve(
    eleve,
    annee,
    classe,
    type_inscription=Inscription.NOUVELLE,
    bulletin_precedent_verifie=False,
):
    if not eleve.actif:
        raise ValidationError(
            "Cet élève est désactivé."
        )

    if annee.statut == AnneeScolaire.CLOTUREE:
        raise ValidationError(
            "Impossible d'inscrire un élève dans une année clôturée."
        )

    if classe.annee_id != annee.id:
        raise ValidationError(
            "La classe doit appartenir à l'année scolaire sélectionnée."
        )

    if Inscription.objects.filter(
        eleve=eleve,
        annee=annee,
    ).exists():
        raise ValidationError(
            "Cet élève possède déjà une inscription pour cette année."
        )

    if type_inscription == Inscription.REINSCRIPTION:
        if not bulletin_precedent_verifie:
            raise ValidationError(
                "Le bulletin de l'année précédente doit être vérifié "
                "avant la réinscription."
            )

    return Inscription.objects.create(
        eleve=eleve,
        annee=annee,
        classe=classe,
        type_inscription=type_inscription,
        bulletin_precedent_verifie=bulletin_precedent_verifie,
    )
