from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from ..models import CompteUtilisateur


def authentifier(login, mot_de_passe):
    """
    Authentifie un utilisateur à partir de son login et
    de son mot de passe.
    """

    try:
        compte = CompteUtilisateur.objects.select_related(
            "utilisateur"
        ).get(login=login)
    except CompteUtilisateur.DoesNotExist:
        return None

    utilisateur = compte.utilisateur

    # Vérification du compte
    if not utilisateur.actif:
        return None

    # Vérification du verrouillage
    if compte.verrouille_jusqu_a:
        if compte.verrouille_jusqu_a > timezone.now():
            return None

        compte.verrouille_jusqu_a = None
        compte.echecs_connexion = 0

    # Vérification du mot de passe
    if not check_password(
        mot_de_passe,
        compte.mot_de_passe_hash
    ):
        compte.echecs_connexion += 1

        # Après plusieurs échecs, on verrouille temporairement
        if compte.echecs_connexion >= 5:
            compte.verrouille_jusqu_a = (
                timezone.now() + timezone.timedelta(minutes=15)
            )

        compte.save(
            update_fields=[
                "echecs_connexion",
                "verrouille_jusqu_a",
            ]
        )

        return None

    # Connexion réussie
    compte.echecs_connexion = 0
    compte.verrouille_jusqu_a = None
    compte.dernier_login = timezone.now()

    compte.save(
        update_fields=[
            "echecs_connexion",
            "verrouille_jusqu_a",
            "dernier_login",
        ]
    )

    return utilisateur


def creer_mot_de_passe(mot_de_passe):
    """
    Transforme un mot de passe en hash sécurisé.
    """
    return make_password(mot_de_passe)

def obtenir_roles_utilisateur(utilisateur):
    """
    Retourne les codes des rôles actifs de l'utilisateur.
    """
    return list(
        utilisateur.attributions_roles
        .filter(
            actif=True,
            role__actif=True
        )
        .values_list(
            'role__code',
            flat=True
        )
    )
    
def ontenir_url_accueil(utilisateur):
    """
    Détermie la page d'accueil selon le rôle
    """
    roles = obtenir_roles_utilisateur(utilisateur)
    priorite = [
        ("ADMIN","dashboard_admin"),
        ("PROMOTEUR","dashboard_promoteur"),
        ("DIRECTEUR","dashboard_directeur"),
        ("PREFET","dashboard_prefet"),
        ("DIRECTEUR_DISCIPLINE","dashboard_discipline"),
        ("COMPTABLE","dashboard_comptabilite"),
        ("CAISSIER","dashboard_caisse"),
        ("SECRETAIRE","dashboard_secretaire"),
        ("ENSEIGNANT","dashboard_enseignant"),
    ]
    for code_role, url_name in priorite:
        if code_role in roles:
            return url_name
    return "accueil"