from .roles import (
    est_comptable,
    est_prefet,
    est_directeur,
)


def peut_enregistrer_paiement(utilisateur):
    """
    Le comptable peut enregistrer un paiement.
    """

    return est_comptable(utilisateur)


def peut_valider_paiement(utilisateur):
    """
    La validation d'un paiement est séparée
    de son enregistrement.
    """

    return (
        est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_generer_recu(utilisateur):
    return (
        est_comptable(utilisateur)
        or est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_annuler_paiement(utilisateur):
    """
    Une annulation nécessite une autorisation supérieure.
    """

    return (
        est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_ouvrir_caisse(utilisateur):
    return (
        est_comptable(utilisateur)
        or est_prefet(utilisateur)
    )


def peut_fermer_caisse(utilisateur):
    return (
        est_comptable(utilisateur)
        or est_prefet(utilisateur)
    )


def peut_enregistrer_entree_caisse(utilisateur):
    return est_comptable(utilisateur)


def peut_demander_sortie_caisse(utilisateur):
    return est_comptable(utilisateur)


def peut_valider_sortie_caisse(utilisateur):
    return (
        est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )


def peut_modifier_calendrier_financier(utilisateur):
    """
    Le calendrier financier est normalement verrouillé.
    """

    return (
        est_prefet(utilisateur)
        or est_directeur(utilisateur)
    )
