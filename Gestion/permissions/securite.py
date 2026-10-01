from .roles import (
    est_admin,
    est_directeur,
    est_prefet,
    est_promoteur,
)


def peut_demander_autorisation(utilisateur):
    """
    Tout utilisateur actif peut éventuellement demander
    une autorisation pour une opération qu'il ne peut
    plus effectuer normalement.
    """

    return utilisateur is not None and utilisateur.actif


def peut_valider_autorisation(utilisateur):
    """
    Seules les autorités habilitées peuvent valider
    une demande d'autorisation.
    """

    return (
        est_directeur(utilisateur)
        or est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )


def peut_consulter_audit(utilisateur):
    return (
        est_admin(utilisateur)
        or est_directeur(utilisateur)
        or est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )


def peut_consulter_anomalies(utilisateur):
    return (
        est_admin(utilisateur)
        or est_directeur(utilisateur)
        or est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )


def peut_traiter_anomalie(utilisateur):
    return (
        est_admin(utilisateur)
        or est_directeur(utilisateur)
        or est_prefet(utilisateur)
    )


def peut_modifier_apres_verrouillage(utilisateur):
    """
    Une modification après verrouillage doit être
    contrôlée par une autorité.
    """

    return (
        est_directeur(utilisateur)
        or est_prefet(utilisateur)
        or est_promoteur(utilisateur)
    )