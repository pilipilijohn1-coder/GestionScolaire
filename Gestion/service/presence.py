from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (
    Presence,
    Horaire,
    Inscription,
)


@transaction.atomic
def enregistrer_presence(
    inscription,
    horaire,
    date_presence,
    statut,
    utilisateur,
):
    if inscription.classe_id != horaire.classe_id:
        raise ValidationError(
            "L'élève et l'horaire doivent appartenir à la même classe."
        )

    # L'utilisateur doit être l'enseignant affecté à cet horaire.
    if hasattr(utilisateur, "enseignant"):
        if horaire.affectation.enseignant.utilisateur_id != utilisateur.id:
            raise ValidationError(
                "Seul l'enseignant affecté à cet horaire peut "
                "saisir la présence."
            )

    presence, _ = Presence.objects.update_or_create(
        inscription=inscription,
        horaire=horaire,
        date_presence=date_presence,
        defaults={
            "statut": statut,
            "saisi_par": utilisateur,
        },
    )

    return presence
