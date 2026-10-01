from .utils import (
    get_utilisateur_permissions,
    get_utilisateur_roles,
)


def permissions_context(request):

    utilisateur = getattr(request, "utilisateur", None)

    if not utilisateur:
        return {
            "permissions_utilisateur": set(),
            "roles_utilisateur": [],
        }

    return {
        "permissions_utilisateur": get_utilisateur_permissions(utilisateur),
        "roles_utilisateur": get_utilisateur_roles(utilisateur),
    }


def session_security_context(request):
    """
    Ajoute des drapeaux de sécurité de session.
    """
    utilisateur_id = request.session.get("utilisateur_id")

    return {
        "session_utilisateur_id": utilisateur_id,
        "session_est_connecte": bool(utilisateur_id),
    }
