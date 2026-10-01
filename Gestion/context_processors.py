from .models import (
    Utilisateur,
    UtilisateurRole,
    RolePermission,
    DestinataireNotification,
)


def utilisateur_connecte(request):

    utilisateur_id = request.session.get("utilisateur_id")

    utilisateur = None
    role = []
    permissions = set()

    if utilisateur_id:

        try:

            utilisateur = (
                Utilisateur.objects
                .get(
                    id=utilisateur_id,
                    actif=True,
                )
            )

            attribution = (
                UtilisateurRole.objects
                .select_related("role")
                .filter(
                    utilisateur=utilisateur,
                    actif=True,
                    role__actif=True,
                )
                .first()
            )

            if attribution:

                role = attribution.role

                codes_permissions = (
                    RolePermission.objects
                    .filter(
                        role=role,
                    )
                    .values_list(
                        "permission__code",
                        flat=True,
                    )
                )

                permissions = set(codes_permissions)

        except Utilisateur.DoesNotExist:

            utilisateur = None

    return {
        "utilisateur_connecte": utilisateur,
        "role_connecte": role,
        "permissions_connecte": permissions,
        "base_template": _base_template_pour_role(role),
        "nb_notifications_non_lues": (
            DestinataireNotification.objects.filter(
                utilisateur=utilisateur,
                lu=False,
            ).count()
            if utilisateur
            else 0
        ),
    }


def _base_template_pour_role(role):

    if not role:

        return "base.html"

    code_role = getattr(role, "code", None)

    if code_role == "ENSEIGNANT":

        return "base_enseignant.html"

    if code_role == "PREFET":

        return "base_prefet.html"

    if code_role == "DIRECTEUR":

        return "base_directeur.html"

    if code_role == "SECRETAIRE":

        return "base_secretaire.html"

    if code_role == "PROMOTEUR":

        return "base_promoteur.html"

    if code_role == "COMPTABLE":

        return "base_comptable.html"

    if code_role == "DIRECTEUR_DISCIPLINE":

        return "base_discipline.html"

    return "base.html"
