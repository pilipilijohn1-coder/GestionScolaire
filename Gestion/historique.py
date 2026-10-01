from .models import (
    TypeAction,
    HistoriqueAction,
)


# ============================================================
# RÉCUPÉRATION DE L'ADRESSE IP
# ============================================================

def get_adresse_ip(request):
    """
    Récupère l'adresse IP du client.

    Si l'application se trouve derrière un proxy,
    X-Forwarded-For peut contenir plusieurs adresses.
    Dans ce cas, nous récupérons la première.
    """

    x_forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if x_forwarded_for:
        adresse_ip = (
            x_forwarded_for
            .split(",")[0]
            .strip()
        )
    else:
        adresse_ip = request.META.get(
            "REMOTE_ADDR"
        )

    return adresse_ip


# ============================================================
# ENREGISTREMENT D'UNE ACTION
# ============================================================

def enregistrer_historique(
    request,
    code_action,
    table_cible=None,
    id_cible=None,
    ancienne_valeur=None,
    nouvelle_valeur=None,
    motif=None,
):
    """
    Enregistre une action dans l'historique du système.

    Paramètres :
        request :
            Requête HTTP actuelle.

        code_action :
            Code unique du TypeAction.
            Exemple :
                "UTILISATEUR_CREATION"

        table_cible :
            Table ou entité concernée.
            Exemple :
                "utilisateur"

        id_cible :
            ID de l'enregistrement concerné.

        ancienne_valeur :
            Ancienne valeur avant modification.

        nouvelle_valeur :
            Nouvelle valeur après modification.

        motif :
            Explication ou motif de l'action.

    Retourne :
        L'objet HistoriqueAction créé,
        ou None si le type d'action n'existe pas.
    """

    # --------------------------------------------------------
    # RÉCUPÉRATION DU TYPE D'ACTION
    # --------------------------------------------------------

    try:
        type_action = TypeAction.objects.get(
            code=code_action
        )

    except TypeAction.DoesNotExist:
        return None


    # --------------------------------------------------------
    # RÉCUPÉRATION DE L'UTILISATEUR CONNECTÉ
    #
    # Le decorators.py place normalement l'utilisateur
    # connecté dans request.utilisateur.
    # --------------------------------------------------------

    utilisateur_connecte = getattr(
        request,
        "utilisateur",
        None
    )


    # --------------------------------------------------------
    # SI request.utilisateur N'EXISTE PAS
    #
    # Nous utilisons la session comme solution de secours.
    # --------------------------------------------------------

    if utilisateur_connecte is None:

        utilisateur_id = request.session.get(
            "utilisateur_id"
        )

        if utilisateur_id:

            from .models import Utilisateur

            try:
                utilisateur_connecte = (
                    Utilisateur.objects.get(
                        id=utilisateur_id
                    )
                )

            except Utilisateur.DoesNotExist:
                utilisateur_connecte = None


    # --------------------------------------------------------
    # CRÉATION DE L'HISTORIQUE
    # --------------------------------------------------------

    historique = HistoriqueAction.objects.create(

        utilisateur=utilisateur_connecte,

        type_action=type_action,

        table_cible=table_cible,

        id_cible=id_cible,

        ancienne_valeur=ancienne_valeur,

        nouvelle_valeur=nouvelle_valeur,

        motif=motif,

        adresse_ip=get_adresse_ip(request),

    )

    return historique
