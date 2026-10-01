from ..models import UtilisateurRole, RolePermission


def get_utilisateur_roles(utilisateur):
    """
    Retourne les rôles actifs de l'utilisateur.
    """
    if not utilisateur:
        return []

    return UtilisateurRole.objects.filter(
        utilisateur=utilisateur,
        actif=True,
        role__actif=True,
    ).select_related("role")


def get_utilisateur_permissions(utilisateur):
    """
    Retourne les codes de permissions actifs
    associés aux rôles de l'utilisateur.
    """
    if not utilisateur:
        return set()

    permissions = RolePermission.objects.filter(
        role__utilisateurrole__utilisateur=utilisateur,
        role__utilisateurrole__actif=True,
        role__actif=True,
    ).select_related("permission")

    return {
        permission.permission.code
        for permission in permissions
    }


def utilisateur_a_permission(utilisateur, permission_code):
    """
    Vérifie si l'utilisateur possède une permission donnée.
    """
    if not utilisateur:
        return False

    return permission_code in get_utilisateur_permissions(utilisateur)


def utilisateur_a_role(utilisateur, role_code):
    """
    Vérifie si l'utilisateur possède un rôle donné.
    """
    if not utilisateur:
        return False

    return UtilisateurRole.objects.filter(
        utilisateur=utilisateur,
        actif=True,
        role__code=role_code,
        role__actif=True,
    ).exists()

def get_utilisateur_permissions(utilisateur):
    if not utilisateur:
        return set()

    roles = UtilisateurRole.objects.filter(
        utilisateur=utilisateur,
        actif=True,
        role__actif=True,
    ).values_list("role_id", flat=True)

    permissions = RolePermission.objects.filter(
        role_id__in=roles
    ).select_related("permission")

    return {
        rp.permission.code
        for rp in permissions
    }
