from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (
    Proclamation,
    ResultatAnnuel,
    Inscription,
    UtilisateurRole,
)


CODE_ROLE_PREFET = "PREFET_ETUDES"


@transaction.atomic
def creer_proclamation_annuelle(
    inscription,
    utilisateur,
):
    roles = utilisateur.roles.filter(
        role__code=CODE_ROLE_PREFET,
        actif=True,
        role__actif=True,
    )

    if not roles.exists():
        raise ValidationError(
            "Seul le préfet des études peut effectuer la proclamation."
        )

    resultat = ResultatAnnuel.objects.filter(
        inscription=inscription,
        annee=inscription.annee,
    ).first()

    if not resultat:
        raise ValidationError(
            "Le résultat annuel n'est pas encore calculé."
        )

    if resultat.verrouille:
        raise ValidationError(
            "Le résultat annuel est déjà verrouillé."
        )

    proclamation, created = Proclamation.objects.get_or_create(
        annee=inscription.annee,
        inscription=inscription,
        type_proclamation=Proclamation.ANNUELLE,
        defaults={
            "utilisateur": utilisateur,
            "statut": Proclamation.VALIDE,
        },
    )

    if not created:
        raise ValidationError(
            "La proclamation annuelle existe déjà."
        )

    return proclamation

def verifier_prefet(utilisateur):
    est_prefet = UtilisateurRole.objects.filter(
    utilisateur=utilisateur,
    role__code="PREFET_ETUDES",
    actif=True,
    ).exists()

    if not est_prefet:
        raise ValidationError(
        "Seul le préfet des études peut effectuer une proclamation."
        )
    
def valider_proclamation(proclamation, utilisateur):
    verifier_prefet(utilisateur)

    # autres vérifications métier...

    proclamation.utilisateur = utilisateur
    proclamation.statut = "VALIDE"
    proclamation.save()

    return proclamation
