from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db import DatabaseError
from django.contrib import messages

from ..models import (
    TypeNotification,
    Notification,
    DestinataireNotification,
    Utilisateur,
    ResponsableLegal,
)


# ============================================================
# TYPE DE NOTIFICATION
# ============================================================

def obtenir_type_notification(code):
    try:
        return TypeNotification.objects.get(
            code=code
        )
    except TypeNotification.DoesNotExist:
        raise ValidationError(
            "Le type de notification n'existe pas."
        )


# ============================================================
# CRÉATION
# ============================================================

@transaction.atomic
def creer_notification(
    type_code,
    objet,
    contenu,
    utilisateur_createur=None,
):
    type_notification = obtenir_type_notification(
        type_code
    )

    if not objet or not objet.strip():
        raise ValidationError(
            "L'objet de la notification est obligatoire."
        )

    if not contenu or not contenu.strip():
        raise ValidationError(
            "Le contenu de la notification est obligatoire."
        )

    notification = Notification.objects.create(
        type_notification=type_notification,
        utilisateur_createur=utilisateur_createur,
        objet=objet.strip(),
        contenu=contenu.strip(),
        statut=Notification.A_ENVOYER,
    )

    return notification


# ============================================================
# AJOUT DESTINATAIRE
# ============================================================

@transaction.atomic
def ajouter_destinataire_utilisateur(
    notification,
    utilisateur,
):
    if not isinstance(utilisateur, Utilisateur):
        raise ValidationError(
            "Utilisateur invalide."
        )

    destinataire = DestinataireNotification.objects.create(
        notification=notification,
        utilisateur=utilisateur,
    )

    return destinataire


@transaction.atomic
def ajouter_destinataire_responsable(
    notification,
    responsable,
):
    if not isinstance(
        responsable,
        ResponsableLegal
    ):
        raise ValidationError(
            "Responsable légal invalide."
        )

    destinataire = DestinataireNotification.objects.create(
        notification=notification,
        responsable=responsable,
    )

    return destinataire


# ============================================================
# ENVOI
# ============================================================

@transaction.atomic
def envoyer_notification(notification_id):
    try:
        notification = (
            Notification.objects
            .select_for_update()
            .get(pk=notification_id)
        )
    except Notification.DoesNotExist:
        raise ValidationError(
            "La notification n'existe pas."
        )

    if notification.statut not in [
        Notification.A_ENVOYER,
        Notification.ECHEC,
    ]:
        raise ValidationError(
            "Cette notification ne peut plus être envoyée."
        )

    destinataires = (
        notification.destinataires
        .select_related(
            "utilisateur",
            "responsable",
        )
    )

    emails = []

    for destinataire in destinataires:

        if destinataire.utilisateur:
            email = destinataire.utilisateur.email

        elif destinataire.responsable:
            email = destinataire.responsable.email

        else:
            continue

        if email:
            emails.append(email)

    if not emails:
        notification.statut = Notification.ECHEC
        notification.save(update_fields=["statut"])

        raise ValidationError(
            "Aucun destinataire ne possède une adresse email."
        )

    try:
        send_mail(
            subject=notification.objet,
            message=notification.contenu,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=emails,
            fail_silently=False,
        )

    except Exception as exc:
        notification.statut = Notification.ECHEC
        notification.save(update_fields=["statut"])

        raise ValidationError(
            f"Échec de l'envoi de la notification : {exc}"
        )

    notification.statut = Notification.ENVOYEE
    notification.save(update_fields=["statut"])

    return notification


# ============================================================
# MARQUER COMME LUE
# ============================================================

@transaction.atomic
def marquer_comme_lue(
    destinataire_id,
):
    try:
        destinataire = (
            DestinataireNotification.objects
            .select_for_update()
            .get(pk=destinataire_id)
        )
    except DestinataireNotification.DoesNotExist:
        raise ValidationError(
            "Le destinataire n'existe pas."
        )

    destinataire.lu = True

    destinataire.save(
        update_fields=["lu"]
    )

    return destinataire


# ============================================================
# NOTIFICATION POUR L'UTILISATEUR CONNECTÉ
# ============================================================

@transaction.atomic
def notification_utilisateur(
    type_code,
    objet,
    contenu,
    utilisateur_createur=None,
    destinataire=None,
):
    """
    Crée une notification et l'envoie à un utilisateur
    (ou à l'utilisateur createur si destinataire est None).
    """
    type_notification = obtenir_type_notification(
        type_code
    )

    notification = Notification.objects.create(
        type_notification=type_notification,
        utilisateur_createur=utilisateur_createur,
        objet=objet.strip(),
        contenu=contenu.strip(),
        statut=Notification.A_ENVOYER,
    )

    if destinataire is None:
        destinataire = utilisateur_createur

    if destinataire is not None:
        DestinataireNotification.objects.create(
            notification=notification,
            utilisateur=destinataire,
        )

    return notification


# ============================================================
# LISTE DES NOTIFICATIONS POUR UN UTILISATEUR
# ============================================================

def notifications_pour_utilisateur(utilisateur):
    """
    Retourne les notifications reçues par un utilisateur,
    triées par date de création (plus récentes d'abord).
    """
    return (
        DestinataireNotification.objects
        .select_related(
            "notification",
            "notification__type_notification",
            "notification__utilisateur_createur",
        )
        .filter(
            utilisateur=utilisateur,
        )
        .order_by("-notification__date_creation")
    )


def nb_notifications_non_lues(utilisateur):
    """
    Compte les notifications non lues pour un utilisateur.
    """
    return DestinataireNotification.objects.filter(
        utilisateur=utilisateur,
        lu=False,
    ).count()


# ============================================================
# MESSAGES → NOTIFICATIONS
# ============================================================

# Longueur maximale de Notification.objet (voir Gestion/models.py).
LONGUEUR_OBJET_NOTIFICATION = 200


def _tronquer(texte, longueur):
    """Rogne un texte a la longueur autorisee, sans le couper au hasard."""
    if texte is None:
        return ""
    texte = str(texte)
    if len(texte) <= longueur:
        return texte
    return texte[: longueur - 3].rstrip() + "..."


def message_vers_notification(
    request,
    type_code,
    objet,
    contenu,
):
    """
    Remplace messages.success/error/warning/info par une
    vraie notification stockée en base pour l'utilisateur
    connecté.
    """
    utilisateur_id = request.session.get(
        "utilisateur_id"
    )

    if not utilisateur_id:
        # Fallback vers le messages framework si pas connecté
        _fallback_to_messages(request, type_code, objet, contenu)
        return

    try:
        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        _fallback_to_messages(request, type_code, objet, contenu)
        return

    try:
        # La colonne notification.objet est limitee a 200 caracteres.
        # SQL Server refuse les chaines plus longues au lieu de les
        # tronquer : on rogne donc l'objet avant tout enregistrement.
        objet = _tronquer(objet, LONGUEUR_OBJET_NOTIFICATION)

        notification_utilisateur(
            type_code=type_code,
            objet=objet,
            contenu=contenu,
            utilisateur_createur=utilisateur,
            destinataire=utilisateur,
        )
    except ValidationError:
        # TypeNotification n'existe pas → fallback
        _fallback_to_messages(request, type_code, objet, contenu)
    except DatabaseError:
        # Contenu trop long, contrainte SQL ou table indisponible :
        # on ne doit jamais faire echouer la requete pour une notification.
        _fallback_to_messages(request, type_code, objet, contenu)


def _fallback_to_messages(
    request,
    type_code,
    objet,
    contenu,
):
    """
    Fallback : utilise le framework messages de Django
    si les notifications par_type ne sont pas disponibles.
    """
    message_text = f"{objet} : {contenu}"

    if type_code == "SUCCESS":
        messages.success(request, message_text)
    elif type_code == "ERROR":
        messages.error(request, message_text)
    elif type_code == "WARNING":
        messages.warning(request, message_text)
    else:
        messages.info(request, message_text)
