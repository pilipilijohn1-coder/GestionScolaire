from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum

from ..models import (
    Paiement,
    Tranche,
)

def montant_paye(tranche):
    resultat = (
        Paiement.objects
        .filter(
            tranche=tranche,
            statut=Paiement.VALIDE,
        )
        .aggregate(total=Sum("montant"))
    )

    return resultat["total"] or Decimal("0.00")

def dette_tranche(tranche):
    paye = montant_paye(tranche)

    reste = tranche.montant - paye

    if reste < 0:
        reste = Decimal("0.00")

    return reste

def tranches_echues_non_soldees(inscription):
    aujourd_hui = timezone.localdate()

    tranches = Tranche.objects.filter(
        date_echeance__lt=aujourd_hui
    ).select_related(
        "frais"
    )

    resultats = []

    for tranche in tranches:
        reste = dette_tranche(tranche)

        if reste > 0:
            resultats.append(
                {
                    "tranche": tranche,
                    "reste": reste,
                }
            )

    return resultats


