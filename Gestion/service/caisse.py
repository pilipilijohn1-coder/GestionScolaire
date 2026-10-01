from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    Caisse,
    Paiement,
    EntreeCaisse,
    SortieCaisse,
    Utilisateur,
)
from Gestion import models


# ============================================================
# UTILITAIRES
# ============================================================

def obtenir_caisse(caisse_id):
    try:
        return Caisse.objects.get(pk=caisse_id)
    except Caisse.DoesNotExist:
        raise ValidationError("La caisse demandée n'existe pas.")


def verifier_caisse_ouverte(caisse):
    if caisse.statut != Caisse.OUVERTE:
        raise ValidationError(
            "Cette opération nécessite une caisse ouverte."
        )


def verifier_montant(montant):
    montant = Decimal(montant)

    if montant <= 0:
        raise ValidationError(
            "Le montant doit être supérieur à zéro."
        )

    return montant


# ============================================================
# OUVERTURE / FERMETURE
# ============================================================

@transaction.atomic
def ouvrir_caisse(caisse_id):
    caisse = obtenir_caisse(caisse_id)

    if caisse.statut == Caisse.OUVERTE:
        raise ValidationError(
            "La caisse est déjà ouverte."
        )

    caisse.statut = Caisse.OUVERTE
    caisse.save(update_fields=["statut"])

    return caisse


@transaction.atomic
def fermer_caisse(caisse_id):
    caisse = obtenir_caisse(caisse_id)

    if caisse.statut == Caisse.FERMEE:
        raise ValidationError(
            "La caisse est déjà fermée."
        )

    caisse.statut = Caisse.FERMEE
    caisse.save(update_fields=["statut"])

    return caisse


# ============================================================
# ENTRÉE DE CAISSE
# ============================================================

@transaction.atomic
def enregistrer_entree(
    caisse_id,
    montant,
    utilisateur,
    paiement=None,
):
    caisse = obtenir_caisse(caisse_id)

    verifier_caisse_ouverte(caisse)
    montant = verifier_montant(montant)

    if not isinstance(utilisateur, Utilisateur):
        raise ValidationError(
            "L'utilisateur responsable de l'opération est invalide."
        )

    if paiement is not None:

        if paiement.statut != Paiement.VALIDE:
            raise ValidationError(
                "Seul un paiement validé peut être enregistré "
                "comme entrée de caisse."
            )

        if montant != paiement.montant:
            raise ValidationError(
                "Le montant de l'entrée doit correspondre "
                "au montant du paiement."
            )

    entree = EntreeCaisse.objects.create(
        caisse=caisse,
        paiement=paiement,
        montant=montant,
        enregistre_par=utilisateur,
    )

    return entree


# ============================================================
# SORTIE DE CAISSE
# ============================================================

@transaction.atomic
def enregistrer_sortie(
    caisse_id,
    montant,
    motif,
    execute_par,
    valide_par=None,
):
    caisse = obtenir_caisse(caisse_id)

    verifier_caisse_ouverte(caisse)
    montant = verifier_montant(montant)

    if not motif or not motif.strip():
        raise ValidationError(
            "Le motif de la sortie de caisse est obligatoire."
        )

    if not isinstance(execute_par, Utilisateur):
        raise ValidationError(
            "L'utilisateur exécutant l'opération est invalide."
        )

    if valide_par is not None:

        if not isinstance(valide_par, Utilisateur):
            raise ValidationError(
                "L'utilisateur validateur est invalide."
            )

        if execute_par.pk == valide_par.pk:
            raise ValidationError(
                "L'utilisateur qui exécute une sortie "
                "ne peut pas être lui-même le validateur."
            )

    sortie = SortieCaisse.objects.create(
        caisse=caisse,
        montant=montant,
        motif=motif.strip(),
        execute_par=execute_par,
        valide_par=valide_par,
    )

    return sortie


# ============================================================
# SOLDE DE CAISSE
# ============================================================

def calculer_solde(caisse_id):
    caisse = obtenir_caisse(caisse_id)

    total_entrees = (
        EntreeCaisse.objects
        .filter(caisse=caisse)
        .aggregate(total=models.Sum("montant"))
    )["total"] or Decimal("0")

    total_sorties = (
        SortieCaisse.objects
        .filter(caisse=caisse)
        .aggregate(total=models.Sum("montant"))
    )["total"] or Decimal("0")

    return total_entrees - total_sorties
