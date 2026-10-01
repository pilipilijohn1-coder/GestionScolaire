from .roles import (
    est_secretaire,
    est_prefet,
    est_directeur,
)


def peut_creer_inscription(utilisateur):
    """
    Le secrétaire peut effectuer les inscriptions.
    Le préfet et le directeur peuvent également
    superviser cette opération.
    """

    return (
        est_secretaire(utilisateur)
        or est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_modifier_inscription(utilisateur):
    return (
        est_secretaire(utilisateur)
        or est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_annuler_inscription(utilisateur):
    """
    Une annulation est une opération sensible.
    """

    return (
        est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_consulter_inscription(utilisateur):
    return (
        est_secretaire(utilisateur)
        or est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_gerer_documents_inscription(utilisateur):
    return est_secretaire(utilisateur)
