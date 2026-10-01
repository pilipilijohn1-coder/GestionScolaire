from .roles import (
    est_directeur_discipline,
    est_prefet,
    est_directeur,
)


def peut_prendre_presence(utilisateur):
    """
    La présence est normalement saisie par l'enseignant
    prévu dans l'horaire.
    """

    return (
        est_directeur_discipline(utilisateur)
        or est_prefet(utilisateur)
    )


def peut_consulter_presence(utilisateur):
    return (
        est_directeur_discipline(utilisateur)
        or est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_gerer_absences(utilisateur):
    return (
        est_directeur_discipline(utilisateur)
        or est_prefet(utilisateur)
    )


def peut_traiter_justification(utilisateur):
    return (
        est_directeur_discipline(utilisateur)
        or est_prefet(utilisateur)
    )
