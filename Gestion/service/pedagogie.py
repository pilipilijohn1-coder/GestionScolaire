from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import (
    Affectation,
    Titularisation,
    AnneeScolaire,
    Enseignant,
    Matiere,
    Classe,
)


@transaction.atomic
def creer_affectation(
    annee,
    enseignant,
    matiere,
    classe,
):
    if annee.statut == AnneeScolaire.CLOTUREE:
        raise ValidationError(
            "Impossible de créer une affectation dans une année clôturée."
        )

    if classe.annee_id != annee.id:
        raise ValidationError(
            "La classe n'appartient pas à cette année scolaire."
        )

    if Affectation.objects.filter(
        annee=annee,
        enseignant=enseignant,
        matiere=matiere,
        classe=classe,
    ).exists():
        raise ValidationError(
            "Cette affectation existe déjà."
        )

    return Affectation.objects.create(
        annee=annee,
        enseignant=enseignant,
        matiere=matiere,
        classe=classe,
    )


@transaction.atomic
def titulariser(
    enseignant,
    classe,
    annee,
):
    if annee.statut == AnneeScolaire.CLOTUREE:
        raise ValidationError(
            "Impossible de titulariser dans une année clôturée."
        )

    # Une classe ne peut avoir qu'un titulaire.
    if Titularisation.objects.filter(
        classe=classe,
        annee=annee,
        statut=Titularisation.ACTIVE,
    ).exists():
        raise ValidationError(
            "Cette classe possède déjà un titulaire."
        )

    # Un enseignant ne peut être titulaire que d'une seule classe.
    if Titularisation.objects.filter(
        enseignant=enseignant,
        annee=annee,
        statut=Titularisation.ACTIVE,
    ).exists():
        raise ValidationError(
            "Cet enseignant est déjà titulaire d'une autre classe."
        )

    return Titularisation.objects.create(
        enseignant=enseignant,
        classe=classe,
        annee=annee,
        statut=Titularisation.ACTIVE,
    )
