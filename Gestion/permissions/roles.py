from Gestion.models import Utilisateur


# ============================================================
# RÔLES DU SYSTÈME
# ============================================================

ADMIN = "ADMIN"
DIRECTEUR = "DIRECTEUR"
PREFET = "PREFET"
SECRETAIRE = "SECRETAIRE"
ENSEIGNANT = "ENSEIGNANT"
ENSEIGNANT_TITULAIRE = "ENSEIGNANT_TITULAIRE"
DIRECTEUR_DISCIPLINE = "DIRECTEUR_DISCIPLINE"
COMPTABLE = "COMPTABLE"
PROMOTEUR = "PROMOTEUR"


ROLES = {
    ADMIN,
    DIRECTEUR,
    PREFET,
    SECRETAIRE,
    ENSEIGNANT,
    ENSEIGNANT_TITULAIRE,
    DIRECTEUR_DISCIPLINE,
    COMPTABLE,
    PROMOTEUR,
}


def utilisateur_a_role(utilisateur, code_role):
    """
    Vérifie si l'utilisateur possède un rôle actif.
    """

    if not utilisateur or not utilisateur.actif:
        return False

    return utilisateur.roles.filter(
        role__code=code_role,
        actif=True,
        role__actif=True,
    ).exists()


def utilisateur_a_un_des_roles(utilisateur, codes_roles):
    """
    Vérifie si l'utilisateur possède au moins
    un des rôles fournis.
    """

    if not utilisateur or not utilisateur.actif:
        return False

    return utilisateur.roles.filter(
        role__code__in=codes_roles,
        actif=True,
        role__actif=True,
    ).exists()


def est_admin(utilisateur):
    return utilisateur_a_role(utilisateur, ADMIN)


def est_directeur(utilisateur):
    return utilisateur_a_role(utilisateur, DIRECTEUR)


def est_prefet(utilisateur):
    return utilisateur_a_role(utilisateur, PREFET)


def est_secretaire(utilisateur):
    return utilisateur_a_role(utilisateur, SECRETAIRE)


def est_enseignant(utilisateur):
    return utilisateur_a_role(utilisateur, ENSEIGNANT)


def est_titulaire(utilisateur):
    return utilisateur_a_role(utilisateur, ENSEIGNANT_TITULAIRE)


def est_directeur_discipline(utilisateur):
    return utilisateur_a_role(utilisateur, DIRECTEUR_DISCIPLINE)


def est_comptable(utilisateur):
    return utilisateur_a_role(utilisateur, COMPTABLE)


def est_promoteur(utilisateur):
    return utilisateur_a_role(utilisateur, PROMOTEUR)
