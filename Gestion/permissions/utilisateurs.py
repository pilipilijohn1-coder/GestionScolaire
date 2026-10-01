from .roles import (
    est_admin,
    est_prefet,
    est_promoteur,
    est_directeur,
)


def peut_creer_utilisateur(utilisateur):
    """
    Seuls les responsables autorisés peuvent créer
    des utilisateurs.
    """

    return (
        est_admin(utilisateur)
        or est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )


def peut_attribuer_role(utilisateur):
    return (
        est_admin(utilisateur)
        or est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )


def peut_desactiver_utilisateur(utilisateur):
    """
    Une désactivation de compte est une opération sensible.
    """

    return (
        est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )


def peut_modifier_utilisateur(utilisateur):
    return (
        est_admin(utilisateur)
        or est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )


def peut_consulter_utilisateurs(utilisateur):
    return (
        est_admin(utilisateur)
        or est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )
