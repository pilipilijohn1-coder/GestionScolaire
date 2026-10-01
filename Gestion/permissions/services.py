from ..models import UtilisateurRole


def utilisateur_a_permission(utilisateur, code_permission):
    """
    Vérifie si un utilisateur possède une permission
    via l'un de ses rôles actifs.
    """

    if not utilisateur:
        return False

    if not utilisateur.actif:
        return False

    return UtilisateurRole.objects.filter(
        utilisateur=utilisateur,
        actif=True,
        role__actif=True,
        role__permissions__permission__code=code_permission,
    ).exists()
