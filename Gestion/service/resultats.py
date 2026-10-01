from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import (
    ResultatPeriode,
    ResultatSemestre,
    ResultatAnnuel,
    Semestre,
    Inscription,
)


def calculer_pourcentage(points, maximum):
    if maximum <= 0:
        raise ValidationError(
            "Le maximum doit être supérieur à zéro."
        )

    valeur = (Decimal(points) / Decimal(maximum)) * Decimal("100")

    return valeur.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


@transaction.atomic
def calculer_resultat_annuel(inscription):
    annee = inscription.annee

    semestres = {
        resultat.semestre.numero: resultat
        for resultat in ResultatSemestre.objects.filter(
            inscription=inscription,
            semestre__annee=annee,
        )
    }

    s1 = semestres.get(1)
    s2 = semestres.get(2)

    if not s1 or not s2:
        raise ValidationError(
            "Les deux résultats semestriels sont nécessaires "
            "pour calculer le résultat annuel."
        )

    points_total = (
        s1.points_total +
        s2.points_total
    )

    points_max = (
        s1.points_max +
        s2.points_max
    )

    pourcentage = calculer_pourcentage(
        points_total,
        points_max,
    )

    resultat, _ = ResultatAnnuel.objects.update_or_create(
        annee=annee,
        inscription=inscription,
        defaults={
            "points_semestre_1": s1.points_total,
            "points_semestre_2": s2.points_total,
            "points_total": points_total,
            "points_max": points_max,
            "pourcentage": pourcentage,
            "statut": ResultatAnnuel.CALCULE,
        },
    )

    return resultat
