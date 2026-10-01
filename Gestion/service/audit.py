from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (
    TypeAction,
    HistoriqueAction,
    Anomalie,
    Utilisateur,
)


# ============================================================
# TYPE D'ACTION
# ============================================================

def obtenir_type_action(code):
    try:
        return TypeAction.objects.get(
            code=code
        )
    except TypeAction.DoesNotExist:
        raise ValidationError(
            "Le type d'action n'existe pas."
        )


# ============================================================
# ENREGISTRER UNE ACTION
# ============================================================

@transaction.atomic
def enregistrer_action(
    code_action,
    utilisateur=None,
    table_cible=None,
    id_cible=None,
    ancienne_valeur=None,
    nouvelle_valeur=None,
    motif=None,
    adresse_ip=None,
):
    type_action = obtenir_type_action(
        code_action
    )

    if utilisateur is not None:
        if not isinstance(
            utilisateur,
            Utilisateur
        ):
            raise ValidationError(
                "Utilisateur invalide."
            )

    historique = HistoriqueAction.objects.create(
        utilisateur=utilisateur,
        type_action=type_action,
        table_cible=table_cible,
        id_cible=id_cible,
        ancienne_valeur=ancienne_valeur,
        nouvelle_valeur=nouvelle_valeur,
        motif=motif,
        adresse_ip=adresse_ip,
    )

    return historique


# ============================================================
# ENREGISTRER UNE ANOMALIE
# ============================================================

@transaction.atomic
def creer_anomalie(
    type_anomalie,
    description,
    gravite=Anomalie.MOYENNE,
):
    if not type_anomalie:
        raise ValidationError(
            "Le type d'anomalie est obligatoire."
        )

    if not description:
        raise ValidationError(
            "La description est obligatoire."
        )

    if gravite not in dict(
        Anomalie.GRAVITE_CHOICES
    ):
        raise ValidationError(
            "Gravité d'anomalie invalide."
        )

    anomalie = Anomalie.objects.create(
        type_anomalie=type_anomalie,
        description=description,
        gravite=gravite,
        statut=Anomalie.OUVERTE,
    )

    return anomalie


# ============================================================
# TRAITER UNE ANOMALIE
# ============================================================

@transaction.atomic
def traiter_anomalie(
    anomalie_id,
    utilisateur,
):
    if not isinstance(
        utilisateur,
        Utilisateur
    ):
        raise ValidationError(
            "Utilisateur invalide."
        )

    try:
        anomalie = (
            Anomalie.objects
            .select_for_update()
            .get(pk=anomalie_id)
        )
    except Anomalie.DoesNotExist:
        raise ValidationError(
            "L'anomalie n'existe pas."
        )

    if anomalie.statut in [
        Anomalie.RESOLUE,
        Anomalie.IGNOREE,
    ]:
        raise ValidationError(
            "Cette anomalie est déjà clôturée."
        )

    anomalie.statut = Anomalie.EN_COURS
    anomalie.traite_par = utilisateur

    anomalie.save(
        update_fields=[
            "statut",
            "traite_par",
        ]
    )

    return anomalie


# ============================================================
# RÉSOUDRE UNE ANOMALIE
# ============================================================

@transaction.atomic
def resoudre_anomalie(
    anomalie_id,
    utilisateur,
):
    if not isinstance(
        utilisateur,
        Utilisateur
    ):
        raise ValidationError(
            "Utilisateur invalide."
        )

    try:
        anomalie = (
            Anomalie.objects
            .select_for_update()
            .get(pk=anomalie_id)
        )
    except Anomalie.DoesNotExist:
        raise ValidationError(
            "L'anomalie n'existe pas."
        )

    anomalie.statut = Anomalie.RESOLUE
    anomalie.traite_par = utilisateur

    anomalie.save(
        update_fields=[
            "statut",
            "traite_par",
        ]
    )

    return anomalie
