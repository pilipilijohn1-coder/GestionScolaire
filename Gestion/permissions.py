from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from .models import (
    Utilisateur,
    UtilisateurRole,
    Permission,
    RolePermission,
)


# ============================================================
# UTILISATEUR CONNECTÉ
# ============================================================

def get_utilisateur_connecte(request):
    """
    Retourne l'utilisateur connecté à partir de la session.
    """

    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return None

    try:
        return Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        return None


# ============================================================
# RÔLES DE L'UTILISATEUR
# ============================================================

def get_roles_utilisateur(utilisateur):
    """
    Retourne les rôles actifs de l'utilisateur.
    """

    if not utilisateur:
        return UtilisateurRole.objects.none()

    return (
        UtilisateurRole.objects
        .select_related("role")
        .filter(
            utilisateur=utilisateur,
            actif=True,
            role__actif=True,
        )
    )


def utilisateur_a_role(utilisateur, code_role):
    """
    Vérifie si l'utilisateur possède un rôle précis.
    """

    return get_roles_utilisateur(utilisateur).filter(
        role__code=code_role
    ).exists()


# ============================================================
# PERMISSIONS
# ============================================================

def utilisateur_a_permission(utilisateur, code_permission):
    """
    Vérifie si l'utilisateur possède une permission.

    Chaîne :

    Utilisateur
        ↓
    UtilisateurRole
        ↓
    Role
        ↓
    RolePermission
        ↓
    Permission
    """

    if not utilisateur:
        return False

    return (
        RolePermission.objects
        .filter(
            role__attributions_utilisateurs__utilisateur=utilisateur,
            role__attributions_utilisateurs__actif=True,
            role__actif=True,
            permission__code=code_permission,
        )
        .exists()
    )


# ============================================================
# DÉCORATEUR DE PERMISSION
# ============================================================

def permission_requise(code_permission):
    """
    Protège une vue avec une permission précise.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            utilisateur = get_utilisateur_connecte(request)

            if not utilisateur:
                return redirect("connexion")

            if not utilisateur_a_permission(
                utilisateur,
                code_permission
            ):
                return HttpResponseForbidden(
                    "Vous n'avez pas la permission "
                    "d'effectuer cette opération."
                )

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator


# ============================================================
# DÉCORATEUR DE RÔLE
# ============================================================

def role_requis(code_role):
    """
    Protège une vue avec un rôle précis.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            utilisateur = get_utilisateur_connecte(request)

            if not utilisateur:
                return redirect("connexion")

            if not utilisateur_a_role(
                utilisateur,
                code_role
            ):
                return HttpResponseForbidden(
                    "Vous n'avez pas le rôle requis "
                    "pour accéder à cette page."
                )

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator
