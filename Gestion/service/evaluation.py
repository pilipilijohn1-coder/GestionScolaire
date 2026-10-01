from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import (
    Evaluation,
    ResultatEvaluation,
    Inscription,
    Affectation,
)


@transaction.atomic
def enregistrer_resultat_evaluation(
    evaluation,
    inscription,
    points_obtenus,
):
    if evaluation.verrouillee:
        raise ValidationError(
            "Cette évaluation est verrouillée."
        )

    if evaluation.statut != Evaluation.OUVERTE:
        raise ValidationError(
            "Cette évaluation n'est plus ouverte."
        )

    if evaluation.affectation.classe_id != inscription.classe_id:
        raise ValidationError(
            "L'élève n'appartient pas à la classe de cette évaluation."
        )

    if points_obtenus < 0:
        raise ValidationError(
            "Les points ne peuvent pas être négatifs."
        )

    if points_obtenus > evaluation.bareme:
        raise ValidationError(
            "Les points obtenus dépassent le barème."
        )

    resultat, created = ResultatEvaluation.objects.update_or_create(
        evaluation=evaluation,
        inscription=inscription,
        defaults={
            "points_obtenus": points_obtenus,
            "verrouille": False,
        },
    )

    return resultat


@transaction.atomic
def verrouiller_evaluation(evaluation):
    if evaluation.statut == Evaluation.VERROUILLEE:
        return evaluation

    evaluation.verrouillee = True
    evaluation.statut = Evaluation.VERROUILLEE

    evaluation.save(
        update_fields=[
            "verrouillee",
            "statut",
        ]
    )

    return evaluation
