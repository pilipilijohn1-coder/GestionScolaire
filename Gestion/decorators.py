from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import (
    Utilisateur,
    UtilisateurRole,
    RolePermission,
)


# ============================================================
# UTILISATEUR CONNECTÉ
# ============================================================

def get_utilisateur_connecte(request):
    """
    Récupère l'utilisateur actuellement connecté
    à partir de la session personnalisée du projet.
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
# CONNEXION REQUISE
# ============================================================

def connexion_requise(view_func):
    """
    Vérifie qu'un utilisateur est connecté.

    Utilisation :

        @connexion_requise
        def ma_vue(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        utilisateur = get_utilisateur_connecte(request)

        # ----------------------------------------------------
        # Utilisateur non connecté
        # ----------------------------------------------------

        if utilisateur is None:

            request.session.flush()

            messages.warning(
                request,
                "Vous devez vous connecter pour accéder à cette page."
            )

            return redirect("connexion")

        # ----------------------------------------------------
        # Rend l'utilisateur disponible dans la vue
        # ----------------------------------------------------

        request.utilisateur = utilisateur

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# RÔLE REQUIS
# ============================================================

def role_requis(*code_roles):
    """
    Vérifie que l'utilisateur possède un ou plusieurs rôles.

    Exemple :

        @role_requis("ADMIN")
        def vue_admin(request):
            ...

        @role_requis("DIRECTEUR_DISCIPLINE", "PREFET")
        def vue_discipline_prefet(request):
            ...
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            utilisateur = get_utilisateur_connecte(request)

            # ------------------------------------------------
            # 1. Vérification de la connexion
            # ------------------------------------------------

            if utilisateur is None:

                request.session.flush()

                messages.warning(
                    request,
                    "Vous devez vous connecter pour accéder à cette page."
                )

                return redirect("connexion")

            # ------------------------------------------------
            # 2. Vérification d'au moins un rôle
            # ------------------------------------------------

            possede_role = (
                UtilisateurRole.objects
                .filter(
                    utilisateur=utilisateur,
                    role__code__in=code_roles,
                    actif=True,
                    role__actif=True,
                )
                .exists()
            )

            # ------------------------------------------------
            # 3. Rôle refusé
            # ------------------------------------------------

            if not possede_role:

                messages.error(
                    request,
                    "Vous n'avez pas le rôle requis pour accéder à cette page."
                )

                return redirect("acces_refuse")

            # ------------------------------------------------
            # 4. Utilisateur disponible dans la vue
            # ------------------------------------------------

            request.utilisateur = utilisateur

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator


# ============================================================
# PERMISSION REQUISE
# ============================================================

def permission_requise(code_permission):
    """
    Vérifie que l'utilisateur possède une permission.

    Exemple :

        @permission_requise("utilisateur.creer")
        def creer_utilisateur(request):
            ...
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            utilisateur = get_utilisateur_connecte(request)

            # ------------------------------------------------
            # 1. Vérification de la connexion
            # ------------------------------------------------

            if utilisateur is None:

                request.session.flush()

                messages.warning(
                    request,
                    "Vous devez vous connecter pour accéder à cette page."
                )

                return redirect("connexion")

            # ------------------------------------------------
            # 2. Récupération des rôles actifs de l'utilisateur
            # ------------------------------------------------

            roles_utilisateur = (
                UtilisateurRole.objects
                .filter(
                    utilisateur=utilisateur,
                    actif=True,
                    role__actif=True,
                )
                .values_list(
                    "role_id",
                    flat=True
                )
            )

            # ------------------------------------------------
            # 3. Vérification de la permission
            # ------------------------------------------------

            possede_permission = (
                RolePermission.objects
                .filter(
                    role_id__in=roles_utilisateur,
                    permission__code=code_permission,
                )
                .exists()
            )

            # ------------------------------------------------
            # 4. Permission refusée
            # ------------------------------------------------

            if not possede_permission:

                messages.error(
                    request,
                    "Vous n'avez pas la permission d'effectuer cette action."
                )

                return redirect("acces_refuse")

            # ------------------------------------------------
            # 5. Utilisateur disponible dans la vue
            # ------------------------------------------------

            request.utilisateur = utilisateur

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator


# ============================================================
# RÔLE OU PERMISSION
# ============================================================

def role_ou_permission_requise(*code_roles, code_permission=None):
    """
    Autorise l'accès si l'utilisateur possède
    l'un des rôles OU la permission demandée.

    Exemple :

        @role_ou_permission_requise(
            "PREFET",
            "DIRECTEUR",
            code_permission="matiere.creer",
        )
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            utilisateur = get_utilisateur_connecte(request)

            # ------------------------------------------------
            # 1. Vérification de la connexion
            # ------------------------------------------------

            if utilisateur is None:

                request.session.flush()

                messages.warning(
                    request,
                    "Vous devez vous connecter pour accéder à cette page."
                )

                return redirect("connexion")

            autorise = False

            # ------------------------------------------------
            # 2. Vérification d'un des rôles
            # ------------------------------------------------

            if code_roles:

                autorise = (
                    UtilisateurRole.objects
                    .filter(
                        utilisateur=utilisateur,
                        role__code__in=code_roles,
                        actif=True,
                        role__actif=True,
                    )
                    .exists()
                )

            # ------------------------------------------------
            # 3. Vérification de la permission
            # ------------------------------------------------

            if not autorise and code_permission:

                roles_utilisateur = (
                    UtilisateurRole.objects
                    .filter(
                        utilisateur=utilisateur,
                        actif=True,
                        role__actif=True,
                    )
                    .values_list(
                        "role_id",
                        flat=True
                    )
                )

                autorise = (
                    RolePermission.objects
                    .filter(
                        role_id__in=roles_utilisateur,
                        permission__code=code_permission,
                    )
                    .exists()
                )

            # ------------------------------------------------
            # 4. Accès refusé
            # ------------------------------------------------

            if not autorise:

                messages.error(
                    request,
                    "Vous n'avez pas les autorisations nécessaires."
                )

                return redirect("acces_refuse")

            # ------------------------------------------------
            # 5. Utilisateur disponible dans la vue
            # ------------------------------------------------

            request.utilisateur = utilisateur

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator
