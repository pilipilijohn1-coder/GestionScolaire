from datetime import datetime
from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q


# ============================================================
# 1. ANNEE SCOLAIRE / STRUCTURE PEDAGOGIQUE
# ============================================================

class AnneeScolaire(models.Model):
    PLANIFIEE = "PLANIFIEE"
    ACTIVE = "ACTIVE"
    CLOTUREE = "CLOTUREE"

    STATUT_CHOICES = [
        (PLANIFIEE, "Planifiée"),
        (ACTIVE, "Active"),
        (CLOTUREE, "Clôturée"),
    ]

    libelle = models.CharField(max_length=20, unique=True)
    date_debut = models.DateField()
    date_fin = models.DateField()

    seuil_passage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=PLANIFIEE,
    )

    class Meta:
        db_table = "annee_scolaire"
        ordering = ["-date_debut"]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    date_fin__gt=models.F("date_debut")),
                name="ck_annee_dates",
            )
        ]

    def clean(self):
        errors = {}

        if self.date_debut and self.date_fin:
            if self.date_fin <= self.date_debut:
                errors["date_fin"] = (
                    "La date de fin doit être postérieure "
                    "à la date de début."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.libelle


class Section(models.Model):
    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=100)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "section"
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle

class Niveau(models.Model):

    code = models.CharField(
        max_length=30,
        unique=True
    )

    libelle = models.CharField(
        max_length=100
    )

    ordre = models.PositiveIntegerField(
        unique=True
    )

    est_ecole_base = models.BooleanField(
        default=False,
        verbose_name="Appartient à l'école de base"
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "niveau"
        ordering = ["ordre"]

    def __str__(self):
        return self.libelle


class Classe(models.Model):

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="classes",
    )

    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="classes",
        null=True,
        blank=True,
    )

    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.PROTECT,
        related_name="classes",
    )

    code = models.CharField(
        max_length=50
    )

    libelle = models.CharField(
        max_length=150
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:

        db_table = "classe"

        ordering = [
            "niveau__ordre",
            "code"
        ]

        constraints = [

            models.UniqueConstraint(
                fields=["annee", "code"],
                name="uq_classe_annee_code",
            ),

        ]
    def clean(self):

        errors = {}

        # --------------------------------------------------------
        # NIVEAU DE L'ÉCOLE DE BASE
        # --------------------------------------------------------

        if (
            self.niveau
            and self.niveau.est_ecole_base
            and self.section is not None
        ):

            errors["section"] = (
                "Une classe appartenant à l'école de base "
                "ne doit pas avoir de section."
            )

        # --------------------------------------------------------
        # NIVEAU AVEC SPÉCIALISATION
        # --------------------------------------------------------

        if (
            self.niveau
            and not self.niveau.est_ecole_base
            and self.section is None
        ):

            errors["section"] = (
                "Une section est obligatoire pour ce niveau."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.libelle

class DomaineEnseignement(models.Model):
    code = models.CharField(max_length=50, unique=True)
    libelle = models.CharField(max_length=150)
    ordre = models.PositiveIntegerField(default=1)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "domaine_enseignement"
        ordering = ["ordre"]

    def __str__(self):
        return self.libelle

class Matiere(models.Model):
    domaine = models.ForeignKey(
        DomaineEnseignement,
        on_delete=models.PROTECT,
        related_name="matieres",null=True,blank=True
    )
    code = models.CharField(max_length=50, unique=True)
    libelle = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "matiere"
        ordering = ["domaine", "libelle"]

    def __str__(self):
        return self.libelle
    
class AffectationMatiere(models.Model):

    # =========================================================
    # CLASSE
    # =========================================================
    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT,
        related_name="affectations_matieres",
    )

    # =========================================================
    # MATIÈRE
    # =========================================================
    matiere = models.ForeignKey(
        Matiere,
        on_delete=models.PROTECT,
        related_name="affectations_classes",
    )

    # =========================================================
    # VOLUME HORAIRE HEBDOMADAIRE
    # =========================================================
    heures_par_semaine = models.PositiveIntegerField(
        default=1,
    )

    # =========================================================
    # STATUT
    # =========================================================
    actif = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "affectation_matiere"

        ordering = [
            "classe",
            "matiere",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "classe",
                    "matiere",
                ],
                name="uq_affectation_classe_matiere",
            ),
        ]

    def clean(self):
        errors = {}

        if self.heures_par_semaine < 1:
            errors["heures_par_semaine"] = (
                "Le nombre d'heures par semaine doit être supérieur à zéro."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.matiere.libelle} - "
            f"{self.classe.libelle}"
        )

# ============================================================
# 2. ELEVES / RESPONSABLES / INSCRIPTIONS
# ============================================================

class Eleve(models.Model):

    matricule = models.CharField(
        max_length=50,
        unique=True
    )

    nom = models.CharField(max_length=80)

    postnom = models.CharField(
        max_length=80,
        blank=True,
        null=True,
    )

    prenom = models.CharField(max_length=80)

    sexe = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        choices=[
            ("M", "Masculin"),
            ("F", "Féminin"),
        ],
    )

    date_naissance = models.DateField(
        blank=True,
        null=True,
    )

    lieu_naissance = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    adresse = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    telephone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    email = models.EmailField(
        max_length=150,
        blank=True,
        null=True,
    )

    photo = models.ImageField(
        upload_to="photos_eleves/",
        blank=True,
        null=True,
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "eleve"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return (
            f"{self.matricule} - "
            f"{self.nom} {self.prenom}"
        )

    @classmethod
    def generer_matricule(cls, classe):
        """Génère un matricule unique au format : YY + 4 lettres section + numéro."""
        annee = getattr(classe, "annee", None)
        if annee and hasattr(annee, "date_fin"):
            yy = str(annee.date_fin.year)[-2:]
        else:
            yy = str(datetime.now().year + 1)[-2:]

        section = getattr(classe, "section", None)
        if section and section.code:
            prefixe_sect = (section.code[:4]).upper().ljust(4, "X")
        else:
            prefixe_sect = "GEST"

        prefixe = f"{yy}{prefixe_sect}"
        dernier = (
            cls.objects
            .filter(matricule__startswith=prefixe)
            .order_by("-id")
            .first()
        )
        if dernier is None:
            numero = 1
        else:
            suffixe = dernier.matricule[len(prefixe):]
            try:
                numero = int(suffixe) + 1
            except ValueError:
                numero = 1
        while cls.objects.filter(matricule=f"{prefixe}{numero:04d}").exists():
            numero += 1
        return f"{prefixe}{numero:04d}"

class ResponsableLegal(models.Model):
    nom = models.CharField(max_length=80)
    postnom = models.CharField(
        max_length=80,
        blank=True,
        null=True,
    )
    prenom = models.CharField(max_length=80)

    telephone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    email = models.EmailField(
        max_length=150,
        blank=True,
        null=True,
    )

    adresse = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    profession = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "responsable_legal"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.nom} {self.prenom}"


class ResponsabiliteScolaire(models.Model):
    PERE = "PERE"
    MERE = "MERE"
    TUTEUR = "TUTEUR"
    AUTRE = "AUTRE"

    TYPE_CHOICES = [
        (PERE, "Père"),
        (MERE, "Mère"),
        (TUTEUR, "Tuteur"),
        (AUTRE, "Autre"),
    ]

    eleve = models.ForeignKey(
        Eleve,
        on_delete=models.PROTECT,
        related_name="responsabilites",
    )

    responsable = models.ForeignKey(
        ResponsableLegal,
        on_delete=models.PROTECT,
        related_name="eleves",
    )

    type_responsabilite = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
    )

    principal = models.BooleanField(default=False)

    autorise_notification = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "responsabilite_scolaire"

        constraints = [
            models.UniqueConstraint(
                fields=["eleve", "responsable"],
                name="uq_responsabilite_eleve_responsable",
            ),

            models.UniqueConstraint(
                fields=["eleve"],
                condition=Q(principal=True),
                name="uq_responsable_principal_eleve",
            ),
        ]

    def __str__(self):
        return f"{self.eleve} - {self.responsable}"


class Inscription(models.Model):
    NOUVELLE = "NOUVELLE"
    REINSCRIPTION = "REINSCRIPTION"

    ACTIVE = "ACTIVE"
    ANNULEE = "ANNULEE"
    TERMINEE = "TERMINEE"
    ABANDON = "ABANDON"

    TYPE_CHOICES = [
        (NOUVELLE, "Nouvelle"),
        (REINSCRIPTION, "Réinscription"),
    ]

    STATUT_CHOICES = [
        (ACTIVE, "Active"),
        (ANNULEE, "Annulée"),
        (TERMINEE, "Terminée"),
        (ABANDON, "Abandon"),
    ]

    eleve = models.ForeignKey(
        Eleve,
        on_delete=models.PROTECT,
        related_name="inscriptions",
    )

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="inscriptions",
    )

    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT,
        related_name="inscriptions",
    )

    date_inscription = models.DateField(
        auto_now_add=True
    )

    type_inscription = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=NOUVELLE,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=ACTIVE,
    )

    bulletin_precedent_verifie = models.BooleanField(
        default=False
    )

    class Meta:
        db_table = "inscription"

        constraints = [
            models.UniqueConstraint(
                fields=["eleve", "annee"],
                name="uq_inscription_eleve_annee",
            ),
        ]

    def clean(self):
        errors = {}

        if self.classe_id and self.annee_id:
            if self.classe.annee_id != self.annee_id:
                errors["classe"] = (
                    "La classe doit appartenir à la même "
                    "année scolaire que l'inscription."
                )

        if (
            self.type_inscription == self.REINSCRIPTION
            and not self.bulletin_precedent_verifie
        ):
            errors["bulletin_precedent_verifie"] = (
                "Une réinscription exige la vérification "
                "du bulletin de l'année précédente."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.eleve} - {self.annee}"


# ============================================================
# 3. UTILISATEURS / ROLES / PERMISSIONS
# ============================================================

class Role(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
    )

    libelle = models.CharField(
        max_length=100,
    )

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "role"

    def __str__(self):
        return self.libelle


class Module(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
    )

    libelle = models.CharField(
        max_length=100,
    )

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "module"

    def __str__(self):
        return self.libelle


class Permission(models.Model):
    code = models.CharField(
        max_length=100,
        unique=True,
    )

    libelle = models.CharField(
        max_length=150,
    )

    class Meta:
        db_table = "permission"

    def __str__(self):
        return self.libelle


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="permissions",
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="roles",
    )

    class Meta:
        db_table = "role_permission"

        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="uq_role_permission",
            ),
        ]

    def __str__(self):
        return f"{self.role} - {self.permission}"


class Utilisateur(models.Model):

    nom = models.CharField(max_length=80)

    postnom = models.CharField(
        max_length=80,
        blank=True,
        null=True,
    )

    prenom = models.CharField(max_length=80)

    email = models.EmailField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
    )

    telephone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    photo_profil = models.ImageField(
        upload_to="photos_profils/",
        blank=True,
        null=True,
    )

    actif = models.BooleanField(
        default=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "utilisateur"

    def __str__(self):
        return (
            f"{self.nom} {self.prenom}"
        )


class UtilisateurRole(models.Model):
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="attributions_roles",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="attributions_utilisateurs",
    )

    date_attribution = models.DateTimeField(
        auto_now_add=True
    )

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "utilisateur_role"

        constraints = [
            models.UniqueConstraint(
                fields=["utilisateur", "role"],
                name="uq_utilisateur_role",
            ),
        ]


class CompteUtilisateur(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="compte",
    )

    login = models.CharField(
        max_length=100,
        unique=True,
    )

    mot_de_passe_hash = models.CharField(
        max_length=500,
    )

    echecs_connexion = models.PositiveIntegerField(
        default=0
    )

    verrouille_jusqu_a = models.DateTimeField(
        blank=True,
        null=True,
    )

    dernier_login = models.DateTimeField(
        blank=True,
        null=True,
    )

    changement_mdp_obligatoire = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "compte_utilisateur"


# ============================================================
# 4. ENSEIGNANTS / AFFECTATIONS / TITULARISATION
# ============================================================

class Enseignant(models.Model):

    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="enseignant",
    )

    matricule = models.CharField(
        max_length=50,
        unique=True,
    )

    grade = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    specialite = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "enseignant"

    def __str__(self):
        return f"{self.matricule} - {self.utilisateur}"

class Affectation(models.Model):

    # =========================================================
    # ENSEIGNANT
    # =========================================================
    enseignant = models.ForeignKey(
        Enseignant,
        on_delete=models.PROTECT,
        related_name="affectations",
    )

    # =========================================================
    # MATIÈRE ATTRIBUÉE À UNE CLASSE
    # =========================================================
    affectation_matiere = models.ForeignKey(
        AffectationMatiere,
        on_delete=models.PROTECT,
        related_name="affectations_enseignants",
        null=True,
        blank=True,
    )

    # =========================================================
    # STATUT
    # =========================================================
    actif = models.BooleanField(
        default=True
    )

    # =========================================================
    # DATE DE CRÉATION
    # =========================================================
    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "affectation"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "enseignant",
                    "affectation_matiere",
                ],
                name="uq_enseignant_affectation_matiere",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.actif
            and self.affectation_matiere_id
        ):
            affectations_actives = Affectation.objects.filter(
                affectation_matiere_id=self.affectation_matiere_id,
                actif=True,
            )

            if self.pk:
                affectations_actives = (
                    affectations_actives.exclude(
                        pk=self.pk
                    )
                )

            if affectations_actives.exists():
                errors["affectation_matiere"] = (
                    "Cette matière est déjà attribuée à "
                    "un autre enseignant actif dans cette classe."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.enseignant} - "
            f"{self.affectation_matiere}"
        )

class Titularisation(models.Model):
    ACTIVE = "ACTIVE"
    TERMINEE = "TERMINEE"
    ANNULEE = "ANNULEE"

    STATUT_CHOICES = [
        (ACTIVE, "Active"),
        (TERMINEE, "Terminée"),
        (ANNULEE, "Annulée"),
    ]

    enseignant = models.ForeignKey(
        Enseignant,
        on_delete=models.PROTECT,
        related_name="titularisations",
    )

    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT,
        related_name="titularisations",
    )

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="titularisations",
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=ACTIVE,
    )

    date_attribution = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "titularisation"

        constraints = [
            models.UniqueConstraint(
                fields=["classe", "annee"],
                condition=Q(statut="ACTIVE"),
                name="uq_titularisation_classe_annee_active",
            ),

            models.UniqueConstraint(
                fields=["enseignant", "annee"],
                condition=Q(statut="ACTIVE"),
                name="uq_titularisation_enseignant_annee_active",
            ),
        ]

    def clean(self):
        errors = {}

        if self.classe_id and self.annee_id:
            if self.classe.annee_id != self.annee_id:
                errors["classe"] = (
                    "La classe doit appartenir à la même "
                    "année scolaire que la titularisation."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.enseignant} - "
            f"{self.classe} - {self.annee}"
        )


# ============================================================
# 5. SEMESTRES / PERIODES
# ============================================================

class Semestre(models.Model):
    OUVERT = "OUVERT"
    CLOTURE = "CLOTURE"
    VERROUILLE = "VERROUILLE"

    STATUT_CHOICES = [
        (OUVERT, "Ouvert"),
        (CLOTURE, "Clôturé"),
        (VERROUILLE, "Verrouillé"),
    ]

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="semestres",
    )

    numero = models.PositiveSmallIntegerField()

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=OUVERT,
    )

    date_ouverture = models.DateField(
        blank=True,
        null=True,
    )

    date_cloture = models.DateField(
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "semestre"

        constraints = [
            models.UniqueConstraint(
                fields=["annee", "numero"],
                name="uq_semestre_annee_numero",
            ),

            models.CheckConstraint(
                condition=Q(numero__in=[1, 2]),
                name="ck_semestre_numero",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.date_ouverture
            and self.date_cloture
            and self.date_cloture < self.date_ouverture
        ):
            errors["date_cloture"] = (
                "La date de clôture doit être postérieure "
                "ou égale à la date d'ouverture."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Semestre {self.numero} - {self.annee}"


class Periode(models.Model):
    OUVERTE = "OUVERTE"
    CLOTUREE = "CLOTUREE"
    VERROUILLEE = "VERROUILLEE"

    STATUT_CHOICES = [
        (OUVERTE, "Ouverte"),
        (CLOTUREE, "Clôturée"),
        (VERROUILLEE, "Verrouillée"),
    ]

    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.PROTECT,
        related_name="periodes",
    )

    numero = models.PositiveSmallIntegerField()

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=OUVERTE,
    )

    date_ouverture = models.DateField(
        blank=True,
        null=True,
    )

    date_cloture = models.DateField(
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "periode"

        constraints = [
            models.UniqueConstraint(
                fields=["semestre", "numero"],
                name="uq_periode_semestre_numero",
            ),

            models.CheckConstraint(
                condition=Q(numero__in=[1, 2]),
                name="ck_periode_numero",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.date_ouverture
            and self.date_cloture
            and self.date_cloture < self.date_ouverture
        ):
            errors["date_cloture"] = (
                "La date de clôture doit être postérieure "
                "ou égale à la date d'ouverture."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Période {self.numero} - {self.semestre}"

class PonderationMatiere(models.Model):
    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.PROTECT,
        related_name="ponderations"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="ponderations_matiere",
        null=True,
        blank=True,
    )
    matiere = models.ForeignKey(
        Matiere,
        on_delete=models.PROTECT,
        related_name="ponderation"
    )

    travaux_journaliers_max = models.PositiveIntegerField()
    examen_max = models.PositiveIntegerField()

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "ponderation_matiere"

        constraints = [
            models.UniqueConstraint(
                fields=["niveau", "section", "matiere"],
                name="uq_ponderation_niveau_section_matiere"
            )
        ]

    @property
    def total_semestre_max(self):
        return (
            self.travaux_journaliers_max * 2
            + self.examen_max 
        )

    def __str__(self):
        section_str = f" - {self.section}" if self.section else ""
        return f"{self.niveau}{section_str} - {self.matiere}"

# ============================================================
# 6. PONDERATIONS
# ============================================================

class ConfigurationPonderation(models.Model):
    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="ponderations",
    )

    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="ponderations",
        blank=True,
        null=True,
    )

    matiere = models.ForeignKey(
        Matiere,
        on_delete=models.PROTECT,
        related_name="ponderations",
        blank=True,
        null=True,
    )

    unite_n = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    poids_periode = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
    )

    poids_examen = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
    )

    poids_semestre = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
    )

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "configuration_ponderation"

    def clean(self):
        if self.unite_n is not None:
            self.poids_periode = self.unite_n
            self.poids_examen = self.unite_n * 2
            self.poids_semestre = self.unite_n * 4

    def save(self, *args, **kwargs):
        self.poids_periode = self.unite_n
        self.poids_examen = self.unite_n * 2
        self.poids_semestre = self.unite_n * 4

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.annee} - n={self.unite_n}"


# ============================================================
# 7. EVALUATIONS
# ============================================================

class Evaluation(models.Model):
    OUVERTE = "OUVERTE"
    CLOTUREE = "CLOTUREE"
    VERROUILLEE = "VERROUILLEE"

    STATUT_CHOICES = [
        (OUVERTE, "Ouverte"),
        (CLOTUREE, "Clôturée"),
        (VERROUILLEE, "Verrouillée"),
    ]

    affectation = models.ForeignKey(
        Affectation,
        on_delete=models.PROTECT,
        related_name="evaluations",
    )

    periode = models.ForeignKey(
        Periode,
        on_delete=models.PROTECT,
        related_name="evaluations",
    )

    libelle = models.CharField(
        max_length=150
    )

    date_evaluation = models.DateField()

    bareme = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    coefficient = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=OUVERTE,
    )

    verrouillee = models.BooleanField(
        default=False
    )

    class Meta:
        db_table = "evaluation"
        ordering = ["date_evaluation", "libelle"]

    def clean(self):
        errors = {}

        if self.periode_id and self.affectation_id:

            if (
                self.periode.semestre.annee_id
                != self.affectation.annee_id
            ):
                errors["periode"] = (
                    "La période doit appartenir à la même "
                    "année scolaire que l'affectation."
                )

            if (
                self.periode.semestre.annee_id
                != self.affectation.classe.annee_id
            ):
                errors["periode"] = (
                    "La période et la classe doivent "
                    "appartenir à la même année scolaire."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.libelle


class ResultatEvaluation(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.PROTECT,
        related_name="resultats",
    )

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.PROTECT,
        related_name="resultats_evaluation",
    )

    points_obtenus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    date_saisie = models.DateTimeField(
        auto_now_add=True
    )

    verrouille = models.BooleanField(
        default=False
    )

    class Meta:
        db_table = "resultat_evaluation"

        constraints = [
            models.UniqueConstraint(
                fields=["evaluation", "inscription"],
                name="uq_resultat_evaluation",
            ),
        ]

    def clean(self):
        errors = {}

        if self.evaluation_id and self.points_obtenus is not None:
            if self.points_obtenus > self.evaluation.bareme:
                errors["points_obtenus"] = (
                    "Les points obtenus ne peuvent pas "
                    "dépasser le barème."
                )

        if (
            self.evaluation_id
            and self.inscription_id
        ):
            if (
                self.evaluation.affectation.classe_id
                != self.inscription.classe_id
            ):
                errors["inscription"] = (
                    "L'évaluation et l'inscription doivent "
                    "concerner la même classe."
                )

            if (
                self.evaluation.affectation.annee_id
                != self.inscription.annee_id
            ):
                errors["inscription"] = (
                    "L'évaluation et l'inscription doivent "
                    "concerner la même année scolaire."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.inscription} - {self.evaluation}"


# ============================================================
# 8. EXAMENS
# ============================================================

class Examen(models.Model):
    OUVERT = "OUVERT"
    CLOTURE = "CLOTURE"
    VERROUILLE = "VERROUILLE"

    STATUT_CHOICES = [
        (OUVERT, "Ouvert"),
        (CLOTURE, "Clôturé"),
        (VERROUILLE, "Verrouillé"),
    ]

    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.PROTECT,
        related_name="examens",
    )

    affectation = models.ForeignKey(
        Affectation,
        on_delete=models.PROTECT,
        related_name="examens",
    )

    libelle = models.CharField(
        max_length=150
    )

    date_examen = models.DateField()

    bareme = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    coefficient = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=OUVERT,
    )

    verrouille = models.BooleanField(
        default=False
    )

    class Meta:
        db_table = "examen"

    def clean(self):
        errors = {}

        if self.semestre_id and self.affectation_id:

            if (
                self.semestre.annee_id
                != self.affectation.annee_id
            ):
                errors["semestre"] = (
                    "Le semestre doit appartenir à la même "
                    "année que l'affectation."
                )

            if (
                self.semestre.annee_id
                != self.affectation.classe.annee_id
            ):
                errors["semestre"] = (
                    "Le semestre et la classe doivent "
                    "appartenir à la même année scolaire."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.libelle


class ResultatExamen(models.Model):
    examen = models.ForeignKey(
        Examen,
        on_delete=models.PROTECT,
        related_name="resultats",
    )

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.PROTECT,
        related_name="resultats_examen",
    )

    points_obtenus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    date_saisie = models.DateTimeField(
        auto_now_add=True
    )

    verrouille = models.BooleanField(
        default=False
    )

    class Meta:
        db_table = "resultat_examen"

        constraints = [
            models.UniqueConstraint(
                fields=["examen", "inscription"],
                name="uq_resultat_examen",
            ),
        ]

    def clean(self):
        errors = {}

        if self.examen_id and self.points_obtenus is not None:
            if self.points_obtenus > self.examen.bareme:
                errors["points_obtenus"] = (
                    "Les points obtenus ne peuvent pas "
                    "dépasser le barème de l'examen."
                )

        if (
            self.examen_id
            and self.inscription_id
        ):
            if (
                self.examen.affectation.classe_id
                != self.inscription.classe_id
            ):
                errors["inscription"] = (
                    "L'examen et l'inscription doivent "
                    "concerner la même classe."
                )

            if (
                self.examen.affectation.annee_id
                != self.inscription.annee_id
            ):
                errors["inscription"] = (
                    "L'examen et l'inscription doivent "
                    "concerner la même année scolaire."
                )

            if (
                self.examen.semestre.annee_id
                != self.inscription.annee_id
            ):
                errors["inscription"] = (
                    "L'examen et l'inscription doivent "
                    "concerner la même année scolaire."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.inscription} - {self.examen}"


# ============================================================
# 9. RESULTATS DE PERIODE / SEMESTRE / ANNEE
# ============================================================

class ResultatPeriode(models.Model):
    CALCULE = "CALCULE"

    periode = models.ForeignKey(
        Periode,
        on_delete=models.PROTECT,
        related_name="resultats",
    )

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.PROTECT,
        related_name="resultats_periode",
    )

    points_obtenus = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    points_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    pourcentage = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    statut = models.CharField(
        max_length=20,
        default=CALCULE,
    )

    verrouille = models.BooleanField(
        default=False
    )

    date_calcul = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "resultat_periode"

        constraints = [
            models.UniqueConstraint(
                fields=["periode", "inscription"],
                name="uq_resultat_periode",
            ),
        ]

    def clean(self):
        errors = {}

        if (
            self.periode_id
            and self.inscription_id
            and self.periode.semestre.annee_id
            != self.inscription.annee_id
        ):
            errors["inscription"] = (
                "La période et l'inscription doivent "
                "appartenir à la même année scolaire."
            )

        if (
            self.points_obtenus is not None
            and self.points_max is not None
            and self.points_obtenus > self.points_max
        ):
            errors["points_obtenus"] = (
                "Les points obtenus ne peuvent pas "
                "dépasser les points maximum."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.inscription} - {self.periode}"


class ResultatSemestre(models.Model):
    CALCULE = "CALCULE"

    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.PROTECT,
        related_name="resultats",
    )

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.PROTECT,
        related_name="resultats_semestre",
    )

    points_periode_1 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    points_periode_2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    points_examen = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    points_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    points_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    pourcentage = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    statut = models.CharField(
        max_length=20,
        default=CALCULE,
    )

    verrouille = models.BooleanField(
        default=False
    )

    date_calcul = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "resultat_semestre"

        constraints = [
            models.UniqueConstraint(
                fields=["semestre", "inscription"],
                name="uq_resultat_semestre",
            ),
        ]

    def clean(self):
        if (
            self.semestre_id
            and self.inscription_id
            and self.semestre.annee_id
            != self.inscription.annee_id
        ):
            raise ValidationError(
                "Le semestre et l'inscription doivent "
                "appartenir à la même année scolaire."
            )

    def __str__(self):
        return f"{self.inscription} - {self.semestre}"


class ResultatAnnuel(models.Model):
    CALCULE = "CALCULE"

    ADMIS = "ADMIS"
    AJOURNE = "AJOURNE"
    REDOUBLE = "REDOUBLE"
    ABANDON = "ABANDON"

    DECISION_CHOICES = [
        (ADMIS, "Admis"),
        (AJOURNE, "Ajourné"),
        (REDOUBLE, "Redouble"),
        (ABANDON, "Abandon"),
    ]

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="resultats_annuels",
    )

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.PROTECT,
        related_name="resultats_annuels",
    )

    points_semestre_1 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    points_semestre_2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    points_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    points_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    pourcentage = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    decision = models.CharField(
        max_length=30,
        choices=DECISION_CHOICES,
        blank=True,
        null=True,
    )

    statut = models.CharField(
        max_length=20,
        default=CALCULE,
    )

    verrouille = models.BooleanField(
        default=False
    )

    date_calcul = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "resultat_annuel"

        constraints = [
            models.UniqueConstraint(
                fields=["annee", "inscription"],
                name="uq_resultat_annuel",
            ),
        ]

    def clean(self):
        if (
            self.annee_id
            and self.inscription_id
            and self.annee_id
            != self.inscription.annee_id
        ):
            raise ValidationError(
                "L'année du résultat annuel doit "
                "correspondre à celle de l'inscription."
            )

    def __str__(self):
        return f"{self.inscription} - {self.annee}"


# ============================================================
# 10. MODELES DE BULLETIN / PROCLAMATION
# ============================================================
class ModeleBulletin(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    libelle = models.CharField(
        max_length=150,
    )

    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.PROTECT,
        related_name="modeles_bulletin",
        null=True,
        blank=True,
    )

    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="modeles_bulletin",
        null=True,
        blank=True,
    )

    version = models.PositiveIntegerField(
        default=1
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "modele_bulletin"

    def clean(self):
        erreurs = {}

        # Un modèle doit être lié soit à un niveau,
        # soit à une section.
        if self.niveau_id and self.section_id:
            erreurs["section"] = (
                "Un modèle de bulletin ne peut pas être lié "
                "simultanément à un niveau et à une section."
            )

        if not self.niveau_id and not self.section_id:
            erreurs["niveau"] = (
                "Le modèle doit être lié à un niveau "
                "ou à une section."
            )

        if erreurs:
            raise ValidationError(erreurs)

    def __str__(self):
        return f"{self.libelle} v{self.version}"
    
class Proclamation(models.Model):
    PERIODE_1 = "PERIODE_1"
    SEMESTRE_1 = "SEMESTRE_1"
    PERIODE_3 = "PERIODE_3"
    ANNUELLE = "ANNUELLE"

    TYPE_CHOICES = [
        (PERIODE_1, "Période 1"),
        (SEMESTRE_1, "Semestre 1"),
        (PERIODE_3, "Période 3"),
        (ANNUELLE, "Annuelle"),
    ]

    BROUILLON = "BROUILLON"
    VALIDE = "VALIDE"
    ANNULEE = "ANNULEE"

    STATUT_CHOICES = [
        (BROUILLON, "Brouillon"),
        (VALIDE, "Validée"),
        (ANNULEE, "Annulée"),
    ]

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="proclamations",
    )

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.PROTECT,
        related_name="proclamations",
    )

    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="proclamations",
    )

    type_proclamation = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
    )

    date_proclamation = models.DateTimeField(
        auto_now_add=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=VALIDE,
    )

    class Meta:
        db_table = "proclamation"

    def clean(self):
        if (
            self.inscription_id
            and self.annee_id
            and self.inscription.annee_id
            != self.annee_id
        ):
            raise ValidationError(
                "L'inscription doit appartenir à la même "
                "année scolaire que la proclamation."
            )

    def __str__(self):
        return (
            f"{self.inscription} - "
            f"{self.type_proclamation}"
        )

class Bulletin(models.Model):
    STATUT_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("VALIDE", "Validé"),
        ("PROCLAME", "Proclamé"),
        ("ARCHIVE", "Archivé"),
    ]

    DECISION_CHOICES = [
        ("", "---------"),
        ("PASSE", "Passe"),
        ("DOUBLE", "Double"),
        ("REPECHAGE", "Repêchage"),
        ("A_DETERMINER", "À déterminer"),
    ]

    inscription = models.OneToOneField(
        "Inscription",
        on_delete=models.PROTECT,
        related_name="bulletin",
    )

    annee_scolaire = models.ForeignKey(
        "AnneeScolaire",
        on_delete=models.PROTECT,
        related_name="bulletins",
    )

    # Informations générales du bulletin
    numero_bulletin = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
    )

    version = models.PositiveIntegerField(default=1)

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="BROUILLON",
    )

    # Résultats généraux
    total_semestre_1 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total_semestre_2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total_annuel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    maximum_annuel = models.PositiveIntegerField(
        default=3040
    )

    pourcentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    place = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    nombre_eleves = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    # Informations disciplinaires
    application = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
    )

    conduite = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
    )

    # Décision finale
    decision = models.CharField(
        max_length=30,
        choices=DECISION_CHOICES,
        blank=True,
        default="",
    )

    observation_decision = models.TextField(
        blank=True,
        null=True,
    )

    # Repêchage
    examen_repechage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
    )

    pourcentage_repechage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
    )

    date_generation = models.DateTimeField(
        auto_now_add=True
    )

    date_validation = models.DateTimeField(
        blank=True,
        null=True,
    )

    date_proclamation = models.DateTimeField(
        blank=True,
        null=True,
    )

    observation = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "bulletin"
        ordering = [
            "annee_scolaire",
            "inscription",
        ]

    def __str__(self):
        return (
            f"Bulletin - {self.inscription.eleve} - "
            f"{self.annee_scolaire}"
        )

    def calculer_totaux(self):
        """
        Calcule les totaux à partir des lignes du bulletin.
        """

        lignes = self.lignes.all()

        self.total_semestre_1 = (
            lignes.aggregate(
                total=Sum("s1_total_obtenu")
            )["total"]
            or Decimal("0.00")
        )

        self.total_semestre_2 = (
            lignes.aggregate(
                total=Sum("s2_total_obtenu")
            )["total"]
            or Decimal("0.00")
        )

        self.total_annuel = (
            self.total_semestre_1
            + self.total_semestre_2
        )

        if self.maximum_annuel:
            self.pourcentage = (
                self.total_annuel
                * Decimal("100")
                / Decimal(str(self.maximum_annuel))
            )

        else:
            self.pourcentage = Decimal("0.00")

    def save(self, *args, **kwargs):
        # Le calcul des lignes doit avoir lieu après
        # leur création. On ne calcule donc pas ici
        # lorsque le bulletin est créé pour la première fois.
        super().save(*args, **kwargs)

class LigneBulletin(models.Model):

    bulletin = models.ForeignKey(
        Bulletin,
        on_delete=models.CASCADE,
        related_name="lignes",
    )

    matiere = models.ForeignKey(
        "Matiere",
        on_delete=models.PROTECT,
        related_name="lignes_bulletins",
    )

    ordre = models.PositiveIntegerField(
        default=1
    )

    # ==================================================
    # PREMIER SEMESTRE
    # ==================================================

    s1_travaux_journaliers_max = models.PositiveIntegerField(
        default=0
    )

    s1_travaux_journaliers_obtenu = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    s1_examen_max = models.PositiveIntegerField(
        default=0
    )

    s1_examen_obtenu = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    s1_total_max = models.PositiveIntegerField(
        default=0
    )

    s1_total_obtenu = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ==================================================
    # DEUXIEME SEMESTRE
    # ==================================================

    s2_travaux_journaliers_max = models.PositiveIntegerField(
        default=0
    )

    s2_travaux_journaliers_obtenu = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    s2_examen_max = models.PositiveIntegerField(
        default=0
    )

    s2_examen_obtenu = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    s2_total_max = models.PositiveIntegerField(
        default=0
    )

    s2_total_obtenu = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ==================================================
    # T.A.
    # ==================================================

    total_annuel_obtenu = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ==================================================
    # EXAMEN DE REPECHAGE
    # ==================================================

    examen_repechage_max = models.PositiveIntegerField(
        default=0,
        blank=True,
    )

    examen_repechage_obtenu = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=True,
    )

    observation = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "ligne_bulletin"

        ordering = [
            "ordre",
            "matiere",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["bulletin", "matiere"],
                name="uq_bulletin_matiere"
            )
        ]

    def calculer_totaux(self):

        self.s1_total_obtenu = (
            self.s1_travaux_journaliers_obtenu
            + self.s1_examen_obtenu
        )

        self.s2_total_obtenu = (
            self.s2_travaux_journaliers_obtenu
            + self.s2_examen_obtenu
        )

        self.total_annuel_obtenu = (
            self.s1_total_obtenu
            + self.s2_total_obtenu
        )

    def clean(self):

        erreurs = {}

        if (
            self.s1_travaux_journaliers_obtenu
            < 0
        ):
            erreurs[
                "s1_travaux_journaliers_obtenu"
            ] = "La note ne peut pas être négative."

        if (
            self.s1_examen_obtenu
            < 0
        ):
            erreurs[
                "s1_examen_obtenu"
            ] = "La note ne peut pas être négative."

        if (
            self.s2_travaux_journaliers_obtenu
            < 0
        ):
            erreurs[
                "s2_travaux_journaliers_obtenu"
            ] = "La note ne peut pas être négative."

        if (
            self.s2_examen_obtenu
            < 0
        ):
            erreurs[
                "s2_examen_obtenu"
            ] = "La note ne peut pas être négative."

        if (
            self.s1_travaux_journaliers_obtenu
            > self.s1_travaux_journaliers_max
        ):
            erreurs[
                "s1_travaux_journaliers_obtenu"
            ] = (
                "La note obtenue ne peut pas "
                "dépasser le maximum."
            )

        if (
            self.s1_examen_obtenu
            > self.s1_examen_max
        ):
            erreurs[
                "s1_examen_obtenu"
            ] = (
                "La note obtenue ne peut pas "
                "dépasser le maximum."
            )

        if (
            self.s2_travaux_journaliers_obtenu
            > self.s2_travaux_journaliers_max
        ):
            erreurs[
                "s2_travaux_journaliers_obtenu"
            ] = (
                "La note obtenue ne peut pas "
                "dépasser le maximum."
            )

        if (
            self.s2_examen_obtenu
            > self.s2_examen_max
        ):
            erreurs[
                "s2_examen_obtenu"
            ] = (
                "La note obtenue ne peut pas "
                "dépasser le maximum."
            )

        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):

        self.calculer_totaux()

        self.s1_total_max = (
            self.s1_travaux_journaliers_max
            + self.s1_examen_max
        )

        self.s2_total_max = (
            self.s2_travaux_journaliers_max
            + self.s2_examen_max
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.matiere.libelle} - "
            f"{self.bulletin}"
        )
# ============================================================
# 11. HORAIRE / PRESENCE / ABANDON
# ============================================================
class ConfigurationHoraire(models.Model):

    # =========================================================
    # ANNÉE SCOLAIRE
    # =========================================================

    annee = models.OneToOneField(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="configuration_horaire",
    )

    # =========================================================
    # DÉBUT DE LA JOURNÉE
    # =========================================================

    heure_debut_journee = models.TimeField(
        verbose_name="Heure de début de la journée"
    )

    # =========================================================
    # DURÉE D'UNE HEURE DE COURS
    # Valeur en minutes.
    # =========================================================

    duree_heure = models.PositiveSmallIntegerField(
        verbose_name="Durée d'une heure de cours"
    )

    # =========================================================
    # NOMBRE D'HEURES DE COURS PAR JOUR
    # La pause n'est pas comprise.
    # =========================================================

    nombre_heures_par_jour = (
        models.PositiveSmallIntegerField(
            verbose_name=(
                "Nombre d'heures de cours par jour"
            )
        )
    )

    # =========================================================
    # POSITION DE LA PAUSE
    # =========================================================

    pause_apres_heure = (
        models.PositiveSmallIntegerField(
            verbose_name=(
                "La pause intervient après l'heure"
            )
        )
    )

    # =========================================================
    # DURÉE DE LA PAUSE
    # Valeur en minutes.
    # =========================================================

    duree_pause = models.PositiveSmallIntegerField(
        verbose_name="Durée de la pause"
    )

    # =========================================================
    # VERROUILLAGE
    #
    # False : configuration en préparation
    # True  : configuration validée et verrouillée
    # =========================================================

    verrouillee = models.BooleanField(
        default=False
    )

    # =========================================================
    # DATES
    # =========================================================

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    # =========================================================
    # CONFIGURATION
    # =========================================================

    class Meta:

        db_table = "configuration_horaire"

        verbose_name = (
            "Configuration horaire"
        )

        verbose_name_plural = (
            "Configurations horaires"
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):

        errors = {}

        # -----------------------------------------------------
        # DURÉE D'UNE HEURE
        # -----------------------------------------------------

        if (
            self.duree_heure is not None
            and self.duree_heure <= 0
        ):

            errors["duree_heure"] = (
                "La durée d'une heure de cours doit "
                "être supérieure à zéro."
            )

        # -----------------------------------------------------
        # NOMBRE D'HEURES
        # -----------------------------------------------------

        if (
            self.nombre_heures_par_jour is not None
            and self.nombre_heures_par_jour < 2
        ):

            errors["nombre_heures_par_jour"] = (
                "La journée doit comporter au moins "
                "deux heures de cours."
            )

        # -----------------------------------------------------
        # DURÉE DE LA PAUSE
        # -----------------------------------------------------

        if (
            self.duree_pause is not None
            and self.duree_pause <= 0
        ):

            errors["duree_pause"] = (
                "La durée de la pause doit être "
                "supérieure à zéro."
            )

        # -----------------------------------------------------
        # POSITION DE LA PAUSE
        # -----------------------------------------------------

        if (
            self.pause_apres_heure is not None
            and self.nombre_heures_par_jour is not None
        ):

            if (
                self.pause_apres_heure < 1
                or self.pause_apres_heure
                >= self.nombre_heures_par_jour
            ):

                errors["pause_apres_heure"] = (
                    "La pause doit intervenir entre "
                    "deux heures de cours."
                )

        if errors:

            raise ValidationError(errors)

    # =========================================================
    # PROTECTION DU VERROUILLAGE
    # =========================================================

    def save(self, *args, **kwargs):

        # Une nouvelle configuration peut toujours être créée.
        if self.pk:

            ancienne_configuration = (
                ConfigurationHoraire.objects.get(
                    pk=self.pk
                )
            )

            # Si elle était déjà verrouillée avant la tentative
            # de modification, on bloque la modification.
            if ancienne_configuration.verrouillee:

                raise ValidationError(
                    "Cette configuration horaire est "
                    "verrouillée et ne peut plus être "
                    "modifiée."
                )

        super().save(*args, **kwargs)

    # =========================================================
    # AFFICHAGE
    # =========================================================

    def __str__(self):

        return (
            f"Configuration horaire - "
            f"{self.annee}"
        )
        
class CreneauHoraire(models.Model):

    # =========================================================
    # TYPES
    # =========================================================

    TYPE_COURS = "COURS"
    TYPE_PAUSE = "PAUSE"

    TYPE_CRENEAU_CHOICES = [
        (
            TYPE_COURS,
            "Cours"
        ),
        (
            TYPE_PAUSE,
            "Pause"
        ),
    ]

    # =========================================================
    # CONFIGURATION
    # =========================================================

    configuration = models.ForeignKey(
        ConfigurationHoraire,
        on_delete=models.PROTECT,
        related_name="creneaux",
    )

    # =========================================================
    # ORDRE DU CRÉNEAU
    # =========================================================

    ordre = models.PositiveSmallIntegerField()

    # =========================================================
    # TYPE
    # =========================================================

    type_creneau = models.CharField(
        max_length=10,
        choices=TYPE_CRENEAU_CHOICES,
    )

    # =========================================================
    # NUMÉRO DE L'HEURE
    #
    # NULL pour la pause.
    # =========================================================

    numero_heure = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
    )

    # =========================================================
    # HEURES
    # =========================================================

    heure_debut = models.TimeField()

    heure_fin = models.TimeField()

    # =========================================================
    # STATUT
    # =========================================================

    actif = models.BooleanField(
        default=True
    )

    # =========================================================
    # CONFIGURATION
    # =========================================================

    class Meta:

        db_table = "creneau_horaire"

        ordering = [
            "configuration",
            "ordre",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "configuration",
                    "ordre",
                ],
                name="uq_configuration_creneau_ordre",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):

        errors = {}

        # -----------------------------------------------------
        # HEURE DE FIN
        # -----------------------------------------------------

        if (
            self.heure_debut
            and self.heure_fin
            and self.heure_fin <= self.heure_debut
        ):

            errors["heure_fin"] = (
                "L'heure de fin doit être postérieure "
                "à l'heure de début."
            )

        # -----------------------------------------------------
        # CRÉNEAU DE COURS
        # -----------------------------------------------------

        if (
            self.type_creneau
            == self.TYPE_COURS
        ):

            if not self.numero_heure:

                errors["numero_heure"] = (
                    "Un créneau de cours doit posséder "
                    "un numéro d'heure."
                )

        # -----------------------------------------------------
        # PAUSE
        # -----------------------------------------------------

        elif (
            self.type_creneau
            == self.TYPE_PAUSE
        ):

            if self.numero_heure is not None:

                errors["numero_heure"] = (
                    "La pause ne doit pas posséder "
                    "de numéro d'heure."
                )

            # Une seule pause dans une configuration.
            pauses = CreneauHoraire.objects.filter(
                configuration=self.configuration,
                type_creneau=self.TYPE_PAUSE,
            )

            if self.pk:

                pauses = pauses.exclude(
                    pk=self.pk
                )

            if pauses.exists():

                errors["type_creneau"] = (
                    "Une seule pause est autorisée "
                    "dans une configuration horaire."
                )

        # -----------------------------------------------------
        # NUMÉRO D'HEURE UNIQUE
        # -----------------------------------------------------

        if (
            self.type_creneau == self.TYPE_COURS
            and self.numero_heure is not None
        ):

            heures_existantes = (
                CreneauHoraire.objects.filter(
                    configuration=self.configuration,
                    numero_heure=self.numero_heure,
                )
            )

            if self.pk:

                heures_existantes = (
                    heures_existantes.exclude(
                        pk=self.pk
                    )
                )

            if heures_existantes.exists():

                errors["numero_heure"] = (
                    "Ce numéro d'heure existe déjà "
                    "dans cette configuration."
                )

        if errors:

            raise ValidationError(errors)

    # =========================================================
    # AFFICHAGE
    # =========================================================

    def __str__(self):

        if (
            self.type_creneau
            == self.TYPE_PAUSE
        ):

            libelle = "Pause"

        else:

            libelle = (
                f"{self.numero_heure}e heure"
            )

        return (
            f"{libelle} - "
            f"{self.heure_debut.strftime('%H:%M')} "
            f"à "
            f"{self.heure_fin.strftime('%H:%M')}"
        )

class RepartitionHoraire(models.Model):

    # =========================================================
    # JOURS DE LA SEMAINE
    # =========================================================

    LUNDI = "LUNDI"
    MARDI = "MARDI"
    MERCREDI = "MERCREDI"
    JEUDI = "JEUDI"
    VENDREDI = "VENDREDI"
    SAMEDI = "SAMEDI"

    JOUR_CHOICES = [
        (LUNDI, "Lundi"),
        (MARDI, "Mardi"),
        (MERCREDI, "Mercredi"),
        (JEUDI, "Jeudi"),
        (VENDREDI, "Vendredi"),
        (SAMEDI, "Samedi"),
    ]

    # =========================================================
    # AFFECTATION
    #
    # Permet de retrouver :
    #
    # Affectation
    #     ├── Enseignant
    #     │
    #     └── AffectationMatiere
    #              ├── Classe
    #              └── Matière
    # =========================================================

    affectation = models.ForeignKey(
        Affectation,
        on_delete=models.PROTECT,
        related_name="repartitions_horaires",
    )

    # =========================================================
    # JOUR
    # =========================================================

    jour = models.CharField(
        max_length=15,
        choices=JOUR_CHOICES,
    )

    # =========================================================
    # CRÉNEAU HORAIRE
    #
    # Seuls les créneaux de type COURS peuvent être utilisés.
    # =========================================================

    creneau = models.ForeignKey(
        CreneauHoraire,
        on_delete=models.PROTECT,
        related_name="repartitions_horaires",
    )

    # =========================================================
    # STATUT
    # =========================================================

    actif = models.BooleanField(
        default=True,
    )

    # =========================================================
    # DATE DE CRÉATION
    # =========================================================

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    # =========================================================
    # CONFIGURATION
    # =========================================================

    class Meta:

        db_table = "repartition_horaire"

        ordering = [
            "jour",
            "creneau__ordre",
        ]

        constraints = [

            # -------------------------------------------------
            # UNE MÊME CLASSE NE PEUT PAS AVOIR DEUX COURS
            # AU MÊME JOUR ET AU MÊME CRÉNEAU.
            #
            # Cette règle est vérifiée dans clean(), car
            # la classe est obtenue via l'affectation.
            # -------------------------------------------------

            # -------------------------------------------------
            # UNE MÊME AFFECTATION NE PEUT PAS ÊTRE PLACÉE
            # DEUX FOIS AU MÊME JOUR ET AU MÊME CRÉNEAU.
            # -------------------------------------------------

            models.UniqueConstraint(
                fields=[
                    "affectation",
                    "jour",
                    "creneau",
                ],
                name=(
                    "uq_repartition_affectation_jour_creneau"
                ),
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):

        errors = {}

        # =====================================================
        # AFFECTATION
        # =====================================================

        if self.affectation_id:

            # -------------------------------------------------
            # L'AFFECTATION DOIT ÊTRE ACTIVE
            # -------------------------------------------------

            if not self.affectation.actif:

                errors["affectation"] = (
                    "Cette affectation enseignant n'est plus active."
                )

            # -------------------------------------------------
            # L'AFFECTATION DOIT POSSÉDER UNE
            # AFFECTATION MATIÈRE
            # -------------------------------------------------

            if not self.affectation.affectation_matiere_id:

                errors["affectation"] = (
                    "Cette affectation n'est associée à "
                    "aucune matière."
                )

        # =====================================================
        # CRÉNEAU
        # =====================================================

        if self.creneau_id:

            # -------------------------------------------------
            # SEUL UN CRÉNEAU DE COURS PEUT RECEVOIR
            # UNE MATIÈRE
            # -------------------------------------------------

            if (
                self.creneau.type_creneau
                != CreneauHoraire.TYPE_COURS
            ):

                errors["creneau"] = (
                    "Une matière ne peut être placée que "
                    "dans un créneau de cours."
                )

        # =====================================================
        # VÉRIFICATIONS NÉCESSITANT
        # AFFECTATION + CRÉNEAU
        # =====================================================

        if (
            self.affectation_id
            and self.affectation.affectation_matiere_id
            and self.creneau_id
        ):

            affectation_matiere = (
                self.affectation.affectation_matiere
            )

            classe = (
                affectation_matiere.classe
            )

            # -------------------------------------------------
            # LE CRÉNEAU DOIT APPARTENIR À LA MÊME
            # ANNÉE SCOLAIRE QUE LA CLASSE
            # -------------------------------------------------

            if (
                classe.annee_id
                != self.creneau.configuration.annee_id
            ):

                errors["creneau"] = (
                    "Le créneau sélectionné n'appartient pas "
                    "à la même année scolaire que la classe "
                    "concernée."
                )

            # -------------------------------------------------
            # L'ENSEIGNANT NE PEUT PAS ENSEIGNER
            # DANS DEUX CLASSES AU MÊME MOMENT
            # -------------------------------------------------

            conflits_enseignant = (
                RepartitionHoraire.objects.filter(
                    jour=self.jour,
                    creneau=self.creneau,
                    actif=True,
                    affectation__enseignant_id=
                    self.affectation.enseignant_id,
                )
            )

            # -------------------------------------------------
            # EN MODIFICATION, ON EXCLUT
            # LA RÉPARTITION ACTUELLE
            # -------------------------------------------------

            if self.pk:

                conflits_enseignant = (
                    conflits_enseignant.exclude(
                        pk=self.pk
                    )
                )

            if conflits_enseignant.exists():

                errors["creneau"] = (
                    "Cet enseignant possède déjà un cours "
                    "dans une autre classe à ce même moment."
                )

            # -------------------------------------------------
            # UNE CLASSE NE PEUT PAS AVOIR
            # DEUX COURS AU MÊME MOMENT
            # -------------------------------------------------

            conflits_classe = (
                RepartitionHoraire.objects.filter(
                    jour=self.jour,
                    creneau=self.creneau,
                    actif=True,
                    affectation__affectation_matiere__classe=
                    classe,
                )
            )

            # -------------------------------------------------
            # EN MODIFICATION
            # -------------------------------------------------

            if self.pk:

                conflits_classe = (
                    conflits_classe.exclude(
                        pk=self.pk
                    )
                )

            if conflits_classe.exists():

                errors["creneau"] = (
                    "Cette classe possède déjà un cours "
                    "à ce jour et à ce créneau."
                )

            # -------------------------------------------------
            # RESPECT DU VOLUME HORAIRE HEBDOMADAIRE
            # -------------------------------------------------

            heures_prevues = (
                affectation_matiere.heures_par_semaine
            )

            repartitions_existantes = (
                RepartitionHoraire.objects.filter(
                    affectation=self.affectation,
                    actif=True,
                )
            )

            # -------------------------------------------------
            # EN MODIFICATION
            # -------------------------------------------------

            if self.pk:

                repartitions_existantes = (
                    repartitions_existantes.exclude(
                        pk=self.pk
                    )
                )

            nombre_heures = (
                repartitions_existantes.count()
            )

            if (
                nombre_heures
                >= heures_prevues
            ):

                errors["affectation"] = (
                    f"La matière "
                    f"« {affectation_matiere.matiere.libelle} » "
                    f"a déjà atteint son volume horaire "
                    f"hebdomadaire de "
                    f"{heures_prevues} heure(s)."
                )

        # =====================================================
        # ERREURS
        # =====================================================

        if errors:

            raise ValidationError(
                errors
            )

    # =========================================================
    # AFFICHAGE
    # =========================================================

    def __str__(self):

        if (
            self.affectation.affectation_matiere_id
        ):

            classe = (
                self.affectation
                .affectation_matiere
                .classe
            )

            matiere = (
                self.affectation
                .affectation_matiere
                .matiere
            )

            return (
                f"{classe.libelle} - "
                f"{self.get_jour_display()} - "
                f"{matiere.libelle}"
            )

        return (
            f"{self.get_jour_display()} - "
            f"{self.affectation}"
        )

class Horaire(models.Model):

    # =========================================================
    # ANNÉE SCOLAIRE
    # =========================================================

    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="horaires",
    )


    # =========================================================
    # CLASSE
    # =========================================================

    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT,
        related_name="horaires",
    )


    # =========================================================
    # AFFECTATION
    #
    # Affectation
    #       ↓
    # AffectationMatiere
    #       ↓
    # Matière + Classe
    # =========================================================

    affectation = models.ForeignKey(
        Affectation,
        on_delete=models.PROTECT,
        related_name="horaires",
    )


    # =========================================================
    # JOUR DE LA SEMAINE
    #
    # L'établissement fonctionne du lundi au samedi.
    # =========================================================

    JOURS_SEMAINE = [
        (1, "Lundi"),
        (2, "Mardi"),
        (3, "Mercredi"),
        (4, "Jeudi"),
        (5, "Vendredi"),
        (6, "Samedi"),
    ]

    jour_semaine = models.PositiveSmallIntegerField(
        choices=JOURS_SEMAINE,
    )


    # =========================================================
    # CRÉNEAU HORAIRE
    #
    # Le créneau fournit :
    #
    # - heure_debut
    # - heure_fin
    # - ordre
    # =========================================================

    creneau = models.ForeignKey(
        CreneauHoraire,
        on_delete=models.PROTECT,
        related_name="horaires",
    )


    # =========================================================
    # SALLE
    # =========================================================

    salle = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )


    # =========================================================
    # STATUT
    # =========================================================

    actif = models.BooleanField(
        default=True
    )


    # =========================================================
    # DATE DE CRÉATION
    # =========================================================

    date_creation = models.DateTimeField(
        auto_now_add=True
    )


    # =========================================================
    # CONFIGURATION
    # =========================================================

    class Meta:

        db_table = "horaire"

        ordering = [
            "jour_semaine",
            "creneau__ordre",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "annee",
                    "classe",
                    "jour_semaine",
                    "creneau",
                ],
                condition=Q(actif=True),
                name=("uq_horaire_actif_classe_jour_creneau"),
            ),
        ]


    # =========================================================
    # VALIDATION DES RÈGLES MÉTIER
    # =========================================================

    def clean(self):

        errors = {}


        # -----------------------------------------------------
        # CLASSE ET ANNÉE
        # -----------------------------------------------------

        if (
            self.classe_id
            and self.annee_id
        ):

            if self.classe.annee_id != self.annee_id:

                errors["classe"] = (
                    "La classe doit appartenir à la même "
                    "année scolaire que l'horaire."
                )


        # -----------------------------------------------------
        # AFFECTATION
        # -----------------------------------------------------

        if self.affectation_id:

            affectation = self.affectation


            # Vérification de l'existence de
            # AffectationMatiere.

            if not affectation.affectation_matiere_id:

                errors["affectation"] = (
                    "Cette affectation ne possède pas de "
                    "matière et de classe associées."
                )

            else:

                affectation_matiere = (
                    affectation.affectation_matiere
                )


                # ---------------------------------------------
                # CLASSE
                # ---------------------------------------------

                if (
                    self.classe_id
                    and affectation_matiere.classe_id
                    != self.classe_id
                ):

                    errors["affectation"] = (
                        "L'affectation doit concerner la "
                        "même classe que l'horaire."
                    )


                if (
                    self.annee_id
                    and affectation_matiere.classe.annee_id
                    != self.annee_id
                ):

                    errors["affectation"] = (
                        "L'affectation doit appartenir à la "
                        "même année scolaire que l'horaire."
                    )


                if (
                    self.actif
                    and not affectation.actif
                ):

                    errors["affectation"] = (
                        "Impossible d'utiliser une affectation "
                        "inactive dans un horaire actif."
                    )


                # ---------------------------------------------
                # AFFECTATION MATIÈRE ACTIVE
                # ---------------------------------------------

                if (
                    self.actif
                    and not affectation_matiere.actif
                ):

                    errors["affectation"] = (
                        "Impossible d'utiliser une matière "
                        "inactive dans un horaire actif."
                    )


        # -----------------------------------------------------
        # CRÉNEAU
        # -----------------------------------------------------

        if self.creneau_id:

            creneau = self.creneau


            # ---------------------------------------------
            # UN CRÉNEAU DE PAUSE NE PEUT PAS CONTENIR
            # UN COURS.
            # ---------------------------------------------

            if (
                creneau.type_creneau
                == CreneauHoraire.TYPE_PAUSE
            ):

                errors["creneau"] = (
                    "Impossible de programmer un cours "
                    "pendant la pause."
                )


            # ---------------------------------------------
            # LE CRÉNEAU DOIT APPARTENIR À LA CONFIGURATION
            # DE LA MÊME ANNÉE SCOLAIRE.
            # ---------------------------------------------

            if (
                self.annee_id
                and creneau.configuration.annee_id
                != self.annee_id
            ):

                errors["creneau"] = (
                    "Le créneau sélectionné ne correspond "
                    "pas à l'année scolaire de l'horaire."
                )


            # ---------------------------------------------
            # LE CRÉNEAU DOIT ÊTRE ACTIF
            # ---------------------------------------------

            if (
                self.actif
                and not creneau.actif
            ):

                errors["creneau"] = (
                    "Impossible d'utiliser un créneau "
                    "inactif dans un horaire actif."
                )


        # -----------------------------------------------------
        # CONTRÔLE DU CONFLIT DE L'ENSEIGNANT
        #
        # Un enseignant ne peut pas enseigner dans deux
        # classes différentes au même moment.
        # -----------------------------------------------------

        if (
            self.actif
            and self.affectation_id
            and self.creneau_id
        ):

            enseignant_id = (
                self.affectation.enseignant_id
            )

            conflits_enseignant = (
                Horaire.objects.filter(
                    annee_id=self.annee_id,
                    jour_semaine=self.jour_semaine,
                    creneau_id=self.creneau_id,
                    actif=True,
                    affectation__enseignant_id=(
                        enseignant_id
                    ),
                )
            )

            # En modification, on exclut l'horaire actuel.

            if self.pk:

                conflits_enseignant = (
                    conflits_enseignant.exclude(
                        pk=self.pk
                    )
                )


            if conflits_enseignant.exists():

                errors["creneau"] = (
                    "Cet enseignant possède déjà un cours "
                    "programmé pendant ce créneau."
                )


        # -----------------------------------------------------
        # ENVOI DES ERREURS
        # -----------------------------------------------------

        if errors:

            raise ValidationError(errors)


    # =========================================================
    # AFFICHAGE
    # =========================================================

    def __str__(self):

        return (
            f"{self.get_jour_semaine_display()} - "
            f"{self.creneau} - "
            f"{self.classe.libelle} - "
            f"{self.affectation}"
        )

class Presence(models.Model):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    RETARD = "RETARD"
    JUSTIFIE = "JUSTIFIE"

    STATUT_CHOICES = [
        (PRESENT, "Présent"),
        (ABSENT, "Absent"),
        (RETARD, "En retard"),
        (JUSTIFIE, "Justifié"),
    ]

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.PROTECT,
        related_name="presences",
    )

    horaire = models.ForeignKey(
        Horaire,
        on_delete=models.PROTECT,
        related_name="presences",
    )

    date_presence = models.DateField()

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
    )

    justification = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    saisi_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="presences_saisies",
    )

    class Meta:
        db_table = "presence"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "inscription",
                    "horaire",
                    "date_presence",
                ],
                name="uq_presence",
            ),
        ]

    def clean(self):
        if (
            self.inscription_id
            and self.horaire_id
            and self.inscription.classe_id
            != self.horaire.classe_id
        ):
            raise ValidationError(
                "La présence et l'horaire doivent "
                "concerner la même classe."
            )


class Abandon(models.Model):
    DECLARE = "DECLARE"
    VALIDE = "VALIDE"
    ANNULE = "ANNULE"

    STATUT_CHOICES = [
        (DECLARE, "Déclaré"),
        (VALIDE, "Validé"),
        (ANNULE, "Annulé"),
    ]

    inscription = models.OneToOneField(
        Inscription,
        on_delete=models.PROTECT,
        related_name="abandon",
    )

    date_abandon = models.DateField()

    motif = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    valide_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="abandons_valides",
        blank=True,
        null=True,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=DECLARE,
    )

    class Meta:
        db_table = "abandon"


# ============================================================
# 12. FINANCES
# ============================================================

class CalendrierFinancier(models.Model):
    OUVERT = "OUVERT"
    CLOTURE = "CLOTURE"

    STATUT_CHOICES = [
        (OUVERT, "Ouvert"),
        (CLOTURE, "Clôturé"),
    ]

    annee = models.OneToOneField(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="calendrier_financier",
    )

    libelle = models.CharField(
        max_length=150
    )

    modifiable = models.BooleanField(
        default=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=OUVERT,
    )

    class Meta:
        db_table = "calendrier_financier"


class FraisScolaires(models.Model):
    annee = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.PROTECT,
        related_name="frais_scolaires",
    )

    libelle = models.CharField(
        max_length=150
    )

    montant_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0"))
        ],
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "frais_scolaires"


class Tranche(models.Model):
    frais = models.ForeignKey(
        FraisScolaires,
        on_delete=models.PROTECT,
        related_name="tranches",
    )

    numero = models.PositiveSmallIntegerField()

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    date_echeance = models.DateField()

    class Meta:
        db_table = "tranche"

        constraints = [
            models.UniqueConstraint(
                fields=["frais", "numero"],
                name="uq_tranche_frais_numero",
            ),
        ]

    def clean(self):
        total_tranches = Decimal("0")

        for tranche in self.frais.tranches.exclude(
            pk=self.pk
        ):
            total_tranches += tranche.montant

        total_tranches += self.montant

        if total_tranches > self.frais.montant_total:
            raise ValidationError(
                "Le total des tranches ne peut pas "
                "dépasser le montant total des frais."
            )


class Paiement(models.Model):
    ENREGISTRE = "ENREGISTRE"
    VALIDE = "VALIDE"
    ANNULE = "ANNULE"

    STATUT_CHOICES = [
        (ENREGISTRE, "Enregistré"),
        (VALIDE, "Validé"),
        (ANNULE, "Annulé"),
    ]

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.PROTECT,
        related_name="paiements",
    )

    tranche = models.ForeignKey(
        Tranche,
        on_delete=models.PROTECT,
        related_name="paiements",
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    date_paiement = models.DateTimeField(
        auto_now_add=True
    )

    enregistre_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="paiements_enregistres",
    )

    valide_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="paiements_valides",
        blank=True,
        null=True,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=ENREGISTRE,
    )

    class Meta:
        db_table = "paiement"

    def clean(self):
        errors = {}

        if (
            self.inscription_id
            and self.tranche_id
            and self.tranche.frais.annee_id
            != self.inscription.annee_id
        ):
            errors["tranche"] = (
                "La tranche doit appartenir à la même "
                "année scolaire que l'inscription."
            )

        if self.tranche_id and self.montant:
            if self.montant > self.tranche.montant:
                errors["montant"] = (
                    "Le paiement ne peut pas dépasser "
                    "le montant de la tranche."
                )

        if self.statut == self.VALIDE and not self.valide_par_id:
            errors["valide_par"] = (
                "Un paiement validé doit avoir "
                "un utilisateur validateur."
            )

        if errors:
            raise ValidationError(errors)


class Recu(models.Model):
    BROUILLON = "BROUILLON"
    VALIDE = "VALIDE"
    ANNULE = "ANNULE"

    STATUT_CHOICES = [
        (BROUILLON, "Brouillon"),
        (VALIDE, "Validé"),
        (ANNULE, "Annulé"),
    ]

    paiement = models.OneToOneField(
        Paiement,
        on_delete=models.PROTECT,
        related_name="recu",
    )

    numero_recu = models.CharField(
        max_length=50,
        unique=True,
    )

    date_generation = models.DateTimeField(
        auto_now_add=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=VALIDE,
    )

    class Meta:
        db_table = "recu"


class Caisse(models.Model):
    OUVERTE = "OUVERTE"
    FERMEE = "FERMEE"

    STATUT_CHOICES = [
        (OUVERTE, "Ouverte"),
        (FERMEE, "Fermée"),
    ]

    libelle = models.CharField(
        max_length=100
    )

    heure_ouverture = models.TimeField()
    heure_fermeture = models.TimeField()

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=FERMEE,
    )

    class Meta:
        db_table = "caisse"

    def clean(self):
        if (
            self.heure_ouverture
            and self.heure_fermeture
            and self.heure_fermeture
            <= self.heure_ouverture
        ):
            raise ValidationError(
                "L'heure de fermeture doit être "
                "postérieure à l'heure d'ouverture."
            )


class EntreeCaisse(models.Model):
    caisse = models.ForeignKey(
        Caisse,
        on_delete=models.PROTECT,
        related_name="entrees",
    )

    paiement = models.ForeignKey(
        Paiement,
        on_delete=models.PROTECT,
        related_name="entrees_caisse",
        blank=True,
        null=True,
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    date_entree = models.DateTimeField(
        auto_now_add=True
    )

    enregistre_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="entrees_caisse_enregistrees",
    )

    class Meta:
        db_table = "entree_caisse"

    def clean(self):
        if self.paiement_id:
            if self.paiement.statut != Paiement.VALIDE:
                raise ValidationError(
                    "Une entrée de caisse liée à un paiement "
                    "doit utiliser un paiement validé."
                )

            if self.montant != self.paiement.montant:
                raise ValidationError(
                    "Le montant de l'entrée doit correspondre "
                    "au montant du paiement."
                )


class SortieCaisse(models.Model):
    ENREGISTREE = "ENREGISTREE"
    VALIDEE = "VALIDEE"
    ANNULEE = "ANNULEE"

    STATUT_CHOICES = [
        (ENREGISTREE, "Enregistrée"),
        (VALIDEE, "Validée"),
        (ANNULEE, "Annulée"),
    ]

    caisse = models.ForeignKey(
        Caisse,
        on_delete=models.PROTECT,
        related_name="sorties",
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    motif = models.CharField(
        max_length=255
    )

    date_sortie = models.DateTimeField(
        auto_now_add=True
    )

    execute_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="sorties_caisse_executees",
    )

    valide_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="sorties_caisse_validees",
        blank=True,
        null=True,
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=ENREGISTREE,
    )

    class Meta:
        db_table = "sortie_caisse"

    def clean(self):
        if (
            self.statut == self.VALIDEE
            and not self.valide_par_id
        ):
            raise ValidationError(
                "Une sortie validée doit avoir "
                "un utilisateur validateur."
            )


# ============================================================
# 13. AUTORISATION / VERROUILLAGE PROGRESSIF
# ============================================================

class DemandeAutorisation(models.Model):
    EN_ATTENTE = "EN_ATTENTE"
    APPROUVEE = "APPROUVEE"
    REFUSEE = "REFUSEE"
    ANNULEE = "ANNULEE"

    STATUT_CHOICES = [
        (EN_ATTENTE, "En attente"),
        (APPROUVEE, "Approuvée"),
        (REFUSEE, "Refusée"),
        (ANNULEE, "Annulée"),
    ]

    utilisateur_demandeur = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="demandes_autorisation",
    )

    type_operation = models.CharField(
        max_length=50
    )

    table_cible = models.CharField(
        max_length=100
    )

    id_cible = models.PositiveIntegerField()

    motif = models.CharField(
        max_length=500
    )

    date_demande = models.DateTimeField(
        auto_now_add=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=EN_ATTENTE,
    )

    utilisateur_validateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="decisions_autorisation",
        blank=True,
        null=True,
    )

    date_decision = models.DateTimeField(
        blank=True,
        null=True,
    )

    commentaire_decision = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "demande_autorisation"

    def clean(self):
        errors = {}

        if (
            self.statut in [
                self.APPROUVEE,
                self.REFUSEE,
            ]
            and not self.utilisateur_validateur_id
        ):
            errors["utilisateur_validateur"] = (
                "Une demande approuvée ou refusée doit "
                "avoir un utilisateur validateur."
            )

        if (
            self.statut in [
                self.APPROUVEE,
                self.REFUSEE,
            ]
            and not self.date_decision
        ):
            errors["date_decision"] = (
                "La date de décision est obligatoire."
            )

        if errors:
            raise ValidationError(errors)


# ============================================================
# 14. HISTORIQUE / ANOMALIES
# ============================================================

class TypeAction(models.Model):
    code = models.CharField(
        max_length=80,
        unique=True,
    )

    libelle = models.CharField(
        max_length=150
    )

    class Meta:
        db_table = "type_action"

    def __str__(self):
        return self.libelle


class HistoriqueAction(models.Model):
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="historiques",
        blank=True,
        null=True,
    )

    type_action = models.ForeignKey(
        TypeAction,
        on_delete=models.PROTECT,
        related_name="historiques",
    )

    table_cible = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    id_cible = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    date_action = models.DateTimeField(
        auto_now_add=True
    )

    ancienne_valeur = models.TextField(
        blank=True,
        null=True,
    )

    nouvelle_valeur = models.TextField(
        blank=True,
        null=True,
    )

    motif = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )

    adresse_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "historique_action"
        ordering = ["-date_action"]


class Anomalie(models.Model):
    FAIBLE = "FAIBLE"
    MOYENNE = "MOYENNE"
    HAUTE = "HAUTE"
    CRITIQUE = "CRITIQUE"

    OUVERTE = "OUVERTE"
    EN_COURS = "EN_COURS"
    RESOLUE = "RESOLUE"
    IGNOREE = "IGNOREE"

    GRAVITE_CHOICES = [
        (FAIBLE, "Faible"),
        (MOYENNE, "Moyenne"),
        (HAUTE, "Haute"),
        (CRITIQUE, "Critique"),
    ]

    STATUT_CHOICES = [
        (OUVERTE, "Ouverte"),
        (EN_COURS, "En cours"),
        (RESOLUE, "Résolue"),
        (IGNOREE, "Ignorée"),
    ]

    type_anomalie = models.CharField(
        max_length=80
    )

    description = models.CharField(
        max_length=1000
    )

    gravite = models.CharField(
        max_length=20,
        choices=GRAVITE_CHOICES,
        default=MOYENNE,
    )

    date_detection = models.DateTimeField(
        auto_now_add=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=OUVERTE,
    )

    traite_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="anomalies_traitees",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "anomalie"


# ============================================================
# 15. NOTIFICATIONS
# ============================================================

class TypeNotification(models.Model):
    code = models.CharField(
        max_length=80,
        unique=True,
    )

    libelle = models.CharField(
        max_length=150
    )

    class Meta:
        db_table = "type_notification"

    def __str__(self):
        return self.libelle


class Notification(models.Model):
    A_ENVOYER = "A_ENVOYER"
    ENVOYEE = "ENVOYEE"
    ECHEC = "ECHEC"
    LUE = "LUE"

    STATUT_CHOICES = [
        (A_ENVOYER, "À envoyer"),
        (ENVOYEE, "Envoyée"),
        (ECHEC, "Échec"),
        (LUE, "Lue"),
    ]

    type_notification = models.ForeignKey(
        TypeNotification,
        on_delete=models.PROTECT,
        related_name="notifications",
    )

    utilisateur_createur = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="notifications_creees",
        blank=True,
        null=True,
    )

    objet = models.CharField(
        max_length=200
    )

    contenu = models.TextField()

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=A_ENVOYER,
    )

    class Meta:
        db_table = "notification"


class DestinataireNotification(models.Model):
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="destinataires",
    )

    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name="notifications_recues",
        blank=True,
        null=True,
    )

    responsable = models.ForeignKey(
        ResponsableLegal,
        on_delete=models.PROTECT,
        related_name="notifications_recues",
        blank=True,
        null=True,
    )

    date_envoi = models.DateTimeField(
        blank=True,
        null=True,
    )

    lu = models.BooleanField(
        default=False
    )

    class Meta:
        db_table = "destinataire_notification"

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(utilisateur__isnull=False)
                    ^ Q(responsable__isnull=False)
                ),
                name="ck_destinataire_un_seul_type",
            ),
        ]

    def clean(self):
        if bool(self.utilisateur_id) == bool(
            self.responsable_id
        ):
            raise ValidationError(
                "Un destinataire doit être soit "
                "un utilisateur, soit un responsable légal."
            )

    def __str__(self):
        if self.utilisateur_id:
            return str(self.utilisateur)

        return str(self.responsable)
