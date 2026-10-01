from .base import utilisateur_a_permission
from .roles import (
    est_enseignant,
    est_prefet,
    est_directeur,
)


def peut_saisir_note(utilisateur, evaluation):
    """
    Un enseignant peut saisir une note uniquement
    pour une affectation qui lui appartient.
    """

    if not est_enseignant(utilisateur):
        return False

    try:
        enseignant = utilisateur.enseignant
    except Exception:
        return False

    if evaluation.verrouillee:
        return False

    if evaluation.statut != "OUVERTE":
        return False

    if evaluation.affectation.enseignant_id != enseignant.id:
        return False

    if evaluation.periode.statut != "OUVERTE":
        return False

    return True


def peut_modifier_resultat(utilisateur, resultat):
    """
    Vérifie si l'utilisateur peut modifier un résultat.
    """

    if resultat.verrouille:
        return False

    evaluation = resultat.evaluation

    if evaluation.verrouillee:
        return False

    if evaluation.statut != "OUVERTE":
        return False

    if evaluation.periode.statut != "OUVERTE":
        return False

    if est_enseignant(utilisateur):

        try:
            enseignant = utilisateur.enseignant
        except Exception:
            return False

        return (
            evaluation.affectation.enseignant_id
            == enseignant.id
        )

    return False


def peut_consulter_resultat(utilisateur, resultat):
    """
    Autorise la consultation d'un résultat.
    """

    if est_prefet(utilisateur):
        return True

    if est_directeur(utilisateur):
        return True

    if est_enseignant(utilisateur):

        try:
            enseignant = utilisateur.enseignant
        except Exception:
            return False

        return (
            resultat.evaluation.affectation.enseignant_id
            == enseignant.id
        )

    return False


def peut_verrouiller_resultats(utilisateur):
    """
    Le verrouillage est une opération sensible.
    """

    return (
        est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )

def peut_consulter_notes(utilisateur):
    return utilisateur_a_permission(
        utilisateur,
        "NOTE_CONSULTER",
    )


def peut_saisir_notes(utilisateur):
    return utilisateur_a_permission(
        utilisateur,
        "NOTE_SAISIR",
    )


def peut_modifier_notes(utilisateur):
    return utilisateur_a_permission(
        utilisateur,
        "NOTE_MODIFIER",
    )


def peut_verrouiller_notes(utilisateur):
    return utilisateur_a_permission(
        utilisateur,
        "NOTE_VERROUILLER",
    )

def peut_modifier_evaluation(utilisateur, evaluation):
    if not utilisateur_a_permission(
        utilisateur,
        "NOTE_MODIFIER",
    ):
        return False

    try:
        enseignant = utilisateur.enseignant
    except Exception:
        return False

    if evaluation.affectation.enseignant_id != enseignant.id:
        return False

    if evaluation.verrouillee:
        return False

    if evaluation.statut != "OUVERTE":
        return False

    return True
