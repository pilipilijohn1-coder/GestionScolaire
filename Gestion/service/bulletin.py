from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import (
    Bulletin,
    LigneBulletin,
    Proclamation,
    ModeleBulletin,
    ResultatAnnuel,
)


@transaction.atomic
def generer_bulletin_annuel(
    proclamation,
    modele,
):
    if proclamation.type_proclamation != Proclamation.ANNUELLE:
        raise ValidationError(
            "Cette opération nécessite une proclamation annuelle."
        )

    if proclamation.statut != Proclamation.VALIDE:
        raise ValidationError(
            "La proclamation doit être validée."
        )

    if not modele.actif:
        raise ValidationError(
            "Le modèle de bulletin n'est plus actif."
        )

    bulletin = Bulletin.objects.create(
        inscription=proclamation.inscription,
        proclamation=proclamation,
        modele=modele,
        statut=Bulletin.BROUILLON,
    )

    return bulletin


@transaction.atomic
def verrouiller_bulletin(bulletin):
    if bulletin.statut == Bulletin.ANNULE:
        raise ValidationError(
            "Un bulletin annulé ne peut pas être verrouillé."
        )

    bulletin.statut = Bulletin.VERROUILLE
    bulletin.save(update_fields=["statut"])

    return bulletin
