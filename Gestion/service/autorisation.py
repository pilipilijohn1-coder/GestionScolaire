from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import DemandeAutorisation


def demander_autorisation(
    utilisateur,
    type_operation,
    table_cible,
    id_cible,
    motif,
):
    if not motif or not motif.strip():
        raise ValidationError(
            "Le motif de la demande est obligatoire."
        )

    demande = DemandeAutorisation.objects.create(
        utilisateur_demandeur=utilisateur,
        type_operation=type_operation,
        table_cible=table_cible,
        id_cible=id_cible,
        motif=motif,
        statut=DemandeAutorisation.EN_ATTENTE,
    )

    return demande


def approuver_autorisation(
    demande,
    validateur,
    commentaire=None,
):
    if demande.statut != DemandeAutorisation.EN_ATTENTE:
        raise ValidationError(
            "Cette demande n'est plus en attente."
        )

    if demande.utilisateur_demandeur_id == validateur.id:
        raise ValidationError(
            "L'utilisateur ne peut pas approuver sa propre demande."
        )

    demande.statut = DemandeAutorisation.APPROUVEE
    demande.utilisateur_validateur = validateur
    demande.date_decision = timezone.now()
    demande.commentaire_decision = commentaire

    demande.save(
        update_fields=[
            "statut",
            "utilisateur_validateur",
            "date_decision",
            "commentaire_decision",
        ]
    )

    return demande


def refuser_autorisation(
    demande,
    validateur,
    commentaire=None,
):
    if demande.statut != DemandeAutorisation.EN_ATTENTE:
        raise ValidationError(
            "Cette demande n'est plus en attente."
        )

    if not commentaire or not commentaire.strip():
        raise ValidationError(
            "Un commentaire est obligatoire lors d'un refus."
        )

    if demande.utilisateur_demandeur_id == validateur.id:
        raise ValidationError(
            "L'utilisateur ne peut pas refuser sa propre demande."
        )

    demande.statut = DemandeAutorisation.REFUSEE
    demande.utilisateur_validateur = validateur
    demande.date_decision = timezone.now()
    demande.commentaire_decision = commentaire

    demande.save(
        update_fields=[
            "statut",
            "utilisateur_validateur",
            "date_decision",
            "commentaire_decision",
        ]
    )

    return demande


def annuler_autorisation(demande, utilisateur):
    if demande.statut != DemandeAutorisation.EN_ATTENTE:
        raise ValidationError(
            "Seule une demande en attente peut être annulée."
        )

    if demande.utilisateur_demandeur_id != utilisateur.id:
        raise ValidationError(
            "Seul le demandeur peut annuler sa demande."
        )

    demande.statut = DemandeAutorisation.ANNULEE
    demande.date_decision = timezone.now()

    demande.save(
        update_fields=[
            "statut",
            "date_decision",
        ]
    )

    return demande


def autorisation_accordee(
    type_operation,
    table_cible,
    id_cible,
):
    return DemandeAutorisation.objects.filter(
        type_operation=type_operation,
        table_cible=table_cible,
        id_cible=id_cible,
        statut=DemandeAutorisation.APPROUVEE,
    ).exists()
