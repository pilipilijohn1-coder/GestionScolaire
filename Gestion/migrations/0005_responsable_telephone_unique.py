"""Le telephone devient l'identifiant du responsable legal.

Les enregistrements experimentaux avaient produit sept responsables
partageant le meme numero, tous sans lien avec un eleve. Cette migration
reporte les liens eventuels vers un seul survivor, supprime les doublons
puis interdit la creation d'un second responsable pour un meme numero.
"""

from django.db import migrations, models


def fusionner_doublons(apps, schema_editor):
    """Regroupe les responsables partageant un telephone.

    Le plus ancien identifiant est conserve. Les responsables sans numero
    ne sont pas concernes : NULL n'est pas une valeur partageable.
    """
    ResponsableLegal = apps.get_model("Gestion", "ResponsableLegal")
    ResponsabiliteScolaire = apps.get_model("Gestion", "ResponsabiliteScolaire")

    vus = {}

    for responsable in (
        ResponsableLegal.objects.filter(telephone__isnull=False)
        .exclude(telephone="")
        .order_by("id")
    ):
        survivor = vus.get(responsable.telephone)

        if survivor is None:
            vus[responsable.telephone] = responsable
            continue

        # Les liens pointent desormais sur le responsable conserve.
        ResponsabiliteScolaire.objects.filter(
            responsable=responsable
        ).update(responsable=survivor)

        responsable.delete()


def deduire_telephone_unique(apps, schema_editor):
    """Rend le telephone unique parmi les responsables existants."""
    ResponsableLegal = apps.get_model("Gestion", "ResponsableLegal")

    vus = set()

    for responsable in (
        ResponsableLegal.objects.filter(telephone__isnull=False)
        .exclude(telephone="")
        .order_by("id")
    ):
        telephone = responsable.telephone.strip()

        if telephone in vus:
            responsable.delete()
            continue

        vus.add(telephone)

        if telephone != responsable.telephone:
            responsable.telephone = telephone
            responsable.save(update_fields=["telephone"])


class Migration(migrations.Migration):

    dependencies = [
        ("Gestion", "0004_remove_ponderationmatiere_uq_ponderation_niveau_matiere_and_more"),
    ]

    operations = [
        migrations.RunPython(fusionner_doublons, migrations.RunPython.noop),
        migrations.RunPython(deduire_telephone_unique, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="responsablelegal",
            constraint=models.UniqueConstraint(
                fields=["telephone"],
                condition=models.Q(("telephone__isnull", False)),
                name="uq_responsable_telephone",
            ),
        ),
    ]