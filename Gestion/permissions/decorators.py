from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .utils import (
    utilisateur_a_permission,
    utilisateur_a_role,
)


def permission_required(permission):
    """
    Protège une vue avec une permission précise.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            utilisateur = request.session.get("utilisateur_id")

            if not utilisateur:
                return redirect("connexion")

            from Gestion.models import Utilisateur

            try:
                utilisateur = Utilisateur.objects.get(
                    id=utilisateur
                )
            except Utilisateur.DoesNotExist:
                request.session.flush()
                return redirect("connexion")

            if not utilisateur_a_permission(
                utilisateur,
                permission,
            ):
                messages.error(
                    request,
                    "Vous n'avez pas l'autorisation "
                    "d'effectuer cette opération."
                )

                return redirect("acces_refuse")

            return view_func(
                request,
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


def role_required(role_code):
    """
    Protège une vue avec un rôle précis.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            utilisateur_id = request.session.get(
                "utilisateur_id"
            )

            if not utilisateur_id:
                return redirect("connexion")

            from Gestion.models import Utilisateur

            try:
                utilisateur = Utilisateur.objects.get(
                    id=utilisateur_id
                )
            except Utilisateur.DoesNotExist:
                request.session.flush()
                return redirect("connexion")

            if not utilisateur_a_role(
                utilisateur,
                role_code,
            ):
                messages.error(
                    request,
                    "Vous n'avez pas le rôle nécessaire "
                    "pour accéder à cette page."
                )

                return redirect("acces_refuse")

            return view_func(
                request,
                *args,
                **kwargs,
            )

        return wrapper

    return decorator
