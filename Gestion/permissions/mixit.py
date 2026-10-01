from django.contrib import messages
from django.shortcuts import redirect

from .utils import utilisateur_a_permission


class PermissionRequiredMixin:

    permission_code = None

    def dispatch(self, request, *args, **kwargs):

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

        if not self.permission_code:
            return super().dispatch(
                request,
                *args,
                **kwargs,
            )

        if not utilisateur_a_permission(
            utilisateur,
            self.permission_code,
        ):
            messages.error(
                request,
                "Accès refusé."
            )

            return redirect("acces_refuse")

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )
