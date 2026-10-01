from Gestion.models import UtilisateurRole, RolePermission


def utilisateur_a_permission(utilisateur, code_permission):
    """
    Vérifie si un utilisateur possède une permission active.
    """

    if not utilisateur:
        return False

    if not utilisateur.actif:
        return False

    return RolePermission.objects.filter(
        role__attributions_utilisateurs__utilisateur=utilisateur,
        role__attributions_utilisateurs__actif=True,
        role__actif=True,
        permission__code=code_permission,
    ).exists()

def utilisateur_a_role(utilisateur, code_role):
    """
    Vérifie si l'utilisateur possède un rôle actif.
    """

    if not utilisateur:
        return False

    if not utilisateur.actif:
        return False

    return UtilisateurRole.objects.filter(
        utilisateur=utilisateur,
        role__code=code_role,
        actif=True,
        role__actif=True,
    ).exists()

def utilisateur_a_toutes_les_permissions(
    utilisateur,
    permissions,
):
    """
    Vérifie que l'utilisateur possède toutes les permissions demandées.
    """

    return all(
        utilisateur_a_permission(
            utilisateur,
            permission,
        )
        for permission in permissions
    )

def utilisateur_a_une_permission(
    utilisateur,
    permissions,
):
    """
    Vérifie qu'un utilisateur possède au moins
    une des permissions demandées.
    """

    return any(
        utilisateur_a_permission(
            utilisateur,
            permission,
        )
        for permission in permissions
    )

def peut_desactiver_utilisateur(
    utilisateur,
    utilisateur_cible,
):
    if not utilisateur_a_permission(
        utilisateur,
        "UTILISATEUR_DESACTIVER",
    ):
        return False

    if utilisateur.id == utilisateur_cible.id:
        return False

    return True
