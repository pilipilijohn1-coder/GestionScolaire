from django import forms

from Gestion.models import Affectation, AffectationMatiere, AnneeScolaire, Classe, ConfigurationHoraire, CreneauHoraire, Eleve, Enseignant, Horaire, Inscription, Matiere, Niveau, PonderationMatiere, RepartitionHoraire, Section, Titularisation, Utilisateur, FraisScolaires, Tranche, ModeleBulletin, ResponsableLegal, ResponsabiliteScolaire


class ModifierUtilisateurForm(forms.ModelForm):

    class Meta:
        model = Utilisateur
        fields = [
            "nom",
            "postnom",
            "prenom",
            "telephone",
            "email",
        ]

        widgets = {
            "nom": forms.TextInput(
                attrs={"placeholder": " "}
            ),
            "postnom": forms.TextInput(
                attrs={"placeholder": " "}
            ),
            "prenom": forms.TextInput(
                attrs={"placeholder": " "}
            ),
            "telephone": forms.TextInput(
                attrs={"placeholder": " "}
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": " "}
            ),
        }

class AnneeScolaireForm(forms.ModelForm):

    class Meta:

        model = AnneeScolaire

        fields = [
            "libelle",
            "date_debut",
            "date_fin",
            "seuil_passage",
        ]

        widgets = {

            "libelle": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : 2026-2027",
                }
            ),

            "date_debut": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "date_fin": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "seuil_passage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                    "placeholder": "Exemple : 50",
                }
            ),
        }

class NiveauForm(forms.ModelForm):

    class Meta:

        model = Niveau

        fields = [
            "code",
            "libelle",
            "ordre",
            "est_ecole_base",
        ]

        widgets = {

            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : N1",
                }
            ),

            "libelle": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : Première année",
                }
            ),

            "ordre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "Exemple : 1",
                }
            ),

            "est_ecole_base": forms.CheckboxInput(
                attrs={
                    "class": "form-checkbox",
                }
            ),

        }


    def clean_ordre(self):

        ordre = self.cleaned_data.get("ordre")

        if ordre is None:
            return ordre

        niveaux_existants = Niveau.objects.filter(
            ordre=ordre
        )

        if self.instance.pk:

            niveaux_existants = (
                niveaux_existants.exclude(
                    pk=self.instance.pk
                )
            )

        if niveaux_existants.exists():

            raise forms.ValidationError(
                "Cet ordre est déjà utilisé par un autre niveau."
            )

        return ordre

class ClasseForm(forms.ModelForm):

    class Meta:

        model = Classe

        fields = [
            "annee",
            "niveau",
            "section",
            "code",
            "libelle",
        ]

        widgets = {

            "annee": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "niveau": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "section": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : 1A",
                }
            ),

            "libelle": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Exemple : Première année A"
                    ),
                }
            ),

        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # --------------------------------------------------
        # ANNÉES SCOLAIRES
        # --------------------------------------------------

        self.fields["annee"].queryset = (
            AnneeScolaire.objects.all().order_by(
                "-date_debut"
            )
        )

        self.fields["annee"].empty_label = (
            "Sélectionnez une année scolaire"
        )


        # --------------------------------------------------
        # NIVEAUX ACTIFS
        # --------------------------------------------------

        self.fields["niveau"].queryset = (
            Niveau.objects.filter(
                actif=True
            ).order_by(
                "ordre"
            )
        )

        self.fields["niveau"].empty_label = (
            "Sélectionnez un niveau"
        )


        # --------------------------------------------------
        # SECTIONS ACTIVES
        # --------------------------------------------------

        self.fields["section"].queryset = (
            Section.objects.filter(
                actif=True
            ).order_by(
                "libelle"
            )
        )

        self.fields["section"].empty_label = (
            "Aucune section"
        )

class MatiereForm(forms.ModelForm):

    class Meta:

        model = Matiere

        fields = [
            "code",
            "libelle",
            "description",
        ]

        widgets = {

            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : MATH",
                }
            ),

            "libelle": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : Mathématiques",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Description facultative de la matière"
                    ),
                    "rows": 4,
                }
            ),

        }


    def clean_code(self):

        code = self.cleaned_data.get(
            "code"
        )

        if code:

            code = code.strip().upper()

        return code


    def clean_libelle(self):

        libelle = self.cleaned_data.get(
            "libelle"
        )

        if libelle:

            libelle = libelle.strip()

        return libelle


def _matieres_ponderation_classe(classe):
    """
    Return active Matiere objects available for the given classe,
    filtered via PonderationMatiere by niveau and section.

    Falls back to Matiere.objects.filter(actif=True) if no
    PonderationMatiere entries exist for the classe's niveau/section.
    """
    if classe.niveau_id is None:
        return Matiere.objects.none()

    ponderations_qs = (
        PonderationMatiere.objects
        .select_related("matiere")
        .filter(
            niveau=classe.niveau,
            actif=True,
            matiere__actif=True,
        )
        .order_by("matiere__libelle")
    )

    if classe.section_id:
        ponderations_qs = ponderations_qs.filter(
            section=classe.section
        )
    else:
        ponderations_qs = ponderations_qs.filter(
            section__isnull=True
        )

    matieres = [
        ponderation.matiere
        for ponderation in ponderations_qs
    ]

    if matieres:
        return Matiere.objects.filter(
            id__in=[m.id for m in matieres]
        ).order_by("libelle")

    return Matiere.objects.filter(actif=True).order_by("libelle")


class AffectationMatiereForm(forms.ModelForm):

    annee = forms.ModelChoiceField(
        queryset=AnneeScolaire.objects.none(),
        required=True,
        label="Année scolaire",
        empty_label="Sélectionnez une année scolaire",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_annee",
            }
        ),
    )

    class Meta:
        model = AffectationMatiere

        fields = [
            "classe",
            "matiere",
            "heures_par_semaine",
        ]

        widgets = {

            "classe": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_classe",
                }
            ),

            "matiere": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_matiere",
                }
            ),

            "heures_par_semaine": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "step": "1",
                    "placeholder": "Nombre d'heures par semaine",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        classe_id = kwargs.pop("classe_id", None)
        super().__init__(*args, **kwargs)

        self.fields["annee"].queryset = (
            AnneeScolaire.objects.all()
            .order_by("-id")
        )

        self.fields["annee"].empty_label = (
            "Sélectionnez une année scolaire"
        )

        if classe_id:
            try:
                classe_preselectionnee = (
                    Classe.objects.get(id=classe_id)
                )
                self.initial["annee"] = (
                    classe_preselectionnee.annee
                )
            except (Classe.DoesNotExist, ValueError):
                pass

        if self.is_bound:
            annee_id = self.data.get("annee")

            if annee_id:
                try:
                    self.fields["classe"].queryset = (
                        Classe.objects.filter(
                            annee_id=annee_id,
                            actif=True,
                        )
                        .select_related(
                            "annee",
                            "niveau",
                            "section",
                        )
                        .order_by("libelle")
                    )
                except (ValueError, TypeError):
                    pass

            classe_id_form = self.data.get("classe")

            if annee_id and classe_id_form:
                try:
                    classe = (
                        Classe.objects.get(
                            id=classe_id_form,
                            annee_id=annee_id,
                            actif=True,
                        )
                    )
                    matieres_disponibles = (
                        _matieres_ponderation_classe(classe)
                    )
                    matieres_affectees = AffectationMatiere.objects.filter(
                        classe=classe
                    ).values_list("matiere_id", flat=True)
                    self.fields["matiere"].queryset = (
                        matieres_disponibles.exclude(
                            id__in=matieres_affectees
                        )
                    )
                except (Classe.DoesNotExist, ValueError, TypeError):
                    pass
        elif self.instance.pk:
            try:
                classe = self.instance.classe
                self.initial["annee"] = classe.annee
                matieres_disponibles = (
                    _matieres_ponderation_classe(classe)
                )
                # Exclure les matières déjà affectées, sauf la courante
                matieres_affectees = AffectationMatiere.objects.filter(
                    classe=classe
                ).exclude(
                    pk=self.instance.pk
                ).values_list("matiere_id", flat=True)
                self.fields["matiere"].queryset = (
                    matieres_disponibles.exclude(
                        id__in=matieres_affectees
                    )
                )
            except AttributeError:
                pass
        elif classe_id:
            try:
                classe = Classe.objects.get(id=classe_id)
                matieres_disponibles = (
                    _matieres_ponderation_classe(classe)
                )
                # Exclure les matières déjà affectées à cette classe
                matieres_affectees = AffectationMatiere.objects.filter(
                    classe=classe
                ).values_list("matiere_id", flat=True)
                matieres_disponibles = matieres_disponibles.exclude(
                    id__in=matieres_affectees
                )
                self.fields["matiere"].queryset = matieres_disponibles
            except (Classe.DoesNotExist, ValueError):
                pass

        self.fields["classe"].empty_label = (
            "Sélectionnez une classe"
        )

        self.fields["matiere"].empty_label = (
            "Sélectionnez une matière"
        )

        self.fields["heures_par_semaine"].label = (
            "Nombre d'heures par semaine"
        )

        if classe_id:
            self.fields["classe"].widget = forms.HiddenInput()
            self.fields["classe"].label = ""
            self.initial["classe"] = int(classe_id)

            self.fields["matiere"].help_text = (
                "Matière à affecter à la classe sélectionnée."
            )
        
        self.fields["heures_par_semaine"].help_text = (
            "Indiquez combien de fois cette matière"
            "doit être enseignée pendant la semaine"
        )

    def clean_heures_par_semaine(self):
        heures = self.cleaned_data.get(
            "heures_par_semaine"
        )

        if heures is None:
            return heures

        if heures < 1:
            raise forms.ValidationError(
                "Le nombre d'heures doit être supérieur à zéro."
            )

        return heures
       
class EnseignantForm(forms.Form):

    # =========================================================
    # INFORMATIONS PERSONNELLES
    # =========================================================

    nom = forms.CharField(
        max_length=80,
        required=True,
        label="Nom",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Entrez le nom",
                "autocomplete": "family-name",
            }
        ),
    )

    postnom = forms.CharField(
        max_length=80,
        required=False,
        label="Postnom",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Entrez le postnom",
            }
        ),
    )

    prenom = forms.CharField(
        max_length=80,
        required=True,
        label="Prénom",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Entrez le prénom",
                "autocomplete": "given-name",
            }
        ),
    )

    email = forms.EmailField(
        max_length=150,
        required=False,
        label="Adresse email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "exemple@email.com",
                "autocomplete": "email",
            }
        ),
    )

    telephone = forms.CharField(
        max_length=30,
        required=False,
        label="Téléphone",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Entrez le numéro de téléphone",
                "autocomplete": "tel",
            }
        ),
    )

    photo_profil = forms.ImageField(
        required=False,
        label="Photo de profil",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
            }
        ),
    )

    # =========================================================
    # INFORMATIONS PROFESSIONNELLES
    # =========================================================

    grade = forms.CharField(
        max_length=100,
        required=False,
        label="Grade",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Exemple : Licencié, Gradué...",
            }
        ),
    )

    specialite = forms.CharField(
        max_length=150,
        required=False,
        label="Spécialité",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Exemple : Mathématiques",
            }
        ),
    )

    # =========================================================
    # INFORMATIONS DE CONNEXION
    # =========================================================

    mot_de_passe = forms.CharField(
        required=True,
        label="Mot de passe",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Entrez le mot de passe",
                "autocomplete": "new-password",
            }
        ),
    )

    confirmation_mot_de_passe = forms.CharField(
        required=True,
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirmez le mot de passe",
                "autocomplete": "new-password",
            }
        ),
    )

    # =========================================================
    # INITIALISATION
    # =========================================================

    def __init__(self, *args, **kwargs):

        self.enseignant = kwargs.pop(
            "enseignant",
            None,
        )

        super().__init__(*args, **kwargs)

        # =====================================================
        # MODE MODIFICATION
        # =====================================================

        if self.enseignant:

            utilisateur = (
                self.enseignant.utilisateur
            )

            self.fields["nom"].initial = (
                utilisateur.nom
            )

            self.fields["postnom"].initial = (
                utilisateur.postnom
            )

            self.fields["prenom"].initial = (
                utilisateur.prenom
            )

            self.fields["email"].initial = (
                utilisateur.email
            )

            self.fields["telephone"].initial = (
                utilisateur.telephone
            )

            self.fields["grade"].initial = (
                self.enseignant.grade
            )

            self.fields["specialite"].initial = (
                self.enseignant.specialite
            )

            # ---------------------------------------------
            # EN MODIFICATION :
            # le mot de passe n'est pas obligatoire.
            # ---------------------------------------------

            self.fields[
                "mot_de_passe"
            ].required = False

            self.fields[
                "confirmation_mot_de_passe"
            ].required = False

    # =========================================================
    # VALIDATION DE L'EMAIL
    # =========================================================

    def clean_email(self):

        email = self.cleaned_data.get(
            "email"
        )

        # -----------------------------------------------------
        # EMAIL FACULTATIF
        # -----------------------------------------------------

        if not email:
            return email

        utilisateurs = (
            Utilisateur.objects.filter(
                email__iexact=email
            )
        )

        # -----------------------------------------------------
        # EN MODIFICATION
        # -----------------------------------------------------

        if self.enseignant:

            utilisateurs = (
                utilisateurs.exclude(
                    id=self.enseignant.utilisateur_id
                )
            )

        if utilisateurs.exists():

            raise forms.ValidationError(
                (
                    "Cette adresse email est déjà "
                    "utilisée par un autre utilisateur."
                )
            )

        return email

    # =========================================================
    # VALIDATION DU MOT DE PASSE
    # =========================================================

    def clean(self):

        cleaned_data = super().clean()

        mot_de_passe = cleaned_data.get(
            "mot_de_passe"
        )

        confirmation_mot_de_passe = (
            cleaned_data.get(
                "confirmation_mot_de_passe"
            )
        )

        # -----------------------------------------------------
        # EN CRÉATION
        # -----------------------------------------------------

        if not self.enseignant:

            if not mot_de_passe:

                self.add_error(
                    "mot_de_passe",
                    (
                        "Le mot de passe est obligatoire "
                        "pour créer le compte."
                    )
                )

            if not confirmation_mot_de_passe:

                self.add_error(
                    "confirmation_mot_de_passe",
                    (
                        "Veuillez confirmer "
                        "le mot de passe."
                    )
                )

        # -----------------------------------------------------
        # VÉRIFICATION DES DEUX MOTS DE PASSE
        # -----------------------------------------------------

        if (
            mot_de_passe
            and confirmation_mot_de_passe
        ):

            if mot_de_passe != confirmation_mot_de_passe:

                self.add_error(
                    "confirmation_mot_de_passe",
                    (
                        "Les deux mots de passe "
                        "ne correspondent pas."
                    )
                )

        return cleaned_data

class AffectationForm(forms.ModelForm):
    annee = forms.ModelChoiceField(
        queryset=AnneeScolaire.objects.none(),
        required=True,
        label="Année scolaire",
        empty_label="Sélectionnez une année scolaire",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_annee",
            }
        )
    )

    classe = forms.ModelChoiceField(
        queryset=Classe.objects.none(),
        required=True,
        label="Classe",
        empty_label="Sélectionnez une classe",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_classe",
            }
        )
    )

    matiere = forms.ModelChoiceField(
        queryset=Matiere.objects.none(),
        required=True,
        label="Matière",
        empty_label="Sélectionnez une matière",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_matiere",
            }
        )
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["annee"].queryset = (
            AnneeScolaire.objects.all()
            .order_by("-id")
        )

        self.fields["enseignant"].queryset = (
            Enseignant.objects.filter(
                actif=True,
                utilisateur__actif=True,
            )
            .select_related(
                "utilisateur"
            )
            .order_by(
                "utilisateur__nom",
                "utilisateur__prenom",
            )
        )


        self.fields["enseignant"].empty_label = (
            "Sélectionnez un enseignant"
        )


        self.fields["enseignant"].label = (
            "Enseignant"
        )
        self.fields["enseignant"].widget.attrs.update(
            {
                "class": "form-select",
                "id": "id_enseignant",
            }
        )
        if self.is_bound:

            annee_id = self.data.get(
                "annee"
            )


            classe_id = self.data.get(
                "classe"
            )

            if annee_id:

                try:

                    self.fields["classe"].queryset = (
                        Classe.objects.filter(
                            annee_id=annee_id
                        )
                        .order_by(
                            "libelle"
                        )
                    )

                except (
                    ValueError,
                    TypeError,
                ):

                    pass

            if annee_id and classe_id:

                try:

                    classe_obj = (
                        Classe.objects.get(
                            id=classe_id,
                            annee_id=annee_id,
                            actif=True,
                        )
                    )

                    matieres_dispo = _matieres_ponderation_classe(classe_obj)

                    # Exclure les matières déjà affectées à un autre enseignant actif
                    matieres_affectees = (
                        AffectationMatiere.objects
                        .filter(
                            classe=classe_obj,
                            actif=True,
                            affectations_enseignants__actif=True,
                        )
                        .values_list("matiere_id", flat=True)
                    )
                    self.fields["matiere"].queryset = (
                        matieres_dispo.exclude(id__in=matieres_affectees)
                    )

                except (
                    ValueError,
                    TypeError,
                ):
                    pass

        elif self.instance.pk:

            affectation_matiere = (
                self.instance.affectation_matiere
            )

            annee = (
                affectation_matiere
                .classe
                .annee
            )


            self.fields["annee"].initial = (
                annee
            )

            self.fields["classe"].queryset = (
                Classe.objects.filter(
                    annee=annee
                )
                
                .order_by(
                    "libelle"
                )
            )


            self.fields["classe"].initial = (
                affectation_matiere.classe
            )

            self.fields["matiere"].queryset = (
                _matieres_ponderation_classe(
                    affectation_matiere.classe
                )
            )


            self.fields["matiere"].initial = (
                affectation_matiere.matiere
            )

    def clean(self):

        cleaned_data = super().clean()

        enseignant = cleaned_data.get(
            "enseignant"
        )


        annee = cleaned_data.get(
            "annee"
        )


        classe = cleaned_data.get(
            "classe"
        )


        matiere = cleaned_data.get(
            "matiere"
        )


        # -----------------------------------------------------
        # ARRÊT SI DES INFORMATIONS MANQUENT
        # -----------------------------------------------------

        if not all([
            enseignant,
            annee,
            classe,
            matiere,
        ]):

            return cleaned_data


        # -----------------------------------------------------
        # VÉRIFICATION DE L'ANNÉE DE LA CLASSE
        # -----------------------------------------------------

        if classe.annee_id != annee.id:

            self.add_error(
                "classe",
                (
                    "La classe sélectionnée n'appartient "
                    "pas à l'année scolaire choisie."
                )
            )

            return cleaned_data


        # -----------------------------------------------------
        # RECHERCHE DE L'AFFECTATION MATIÈRE
        # -----------------------------------------------------

        try:

            affectation_matiere = (
                AffectationMatiere.objects.get(
                    classe=classe,
                    classe__annee=annee,
                    matiere=matiere,
                    actif=True,
                )
            )

        except AffectationMatiere.DoesNotExist:

            try:

                ponderation = (
                    PonderationMatiere.objects
                    .select_related("matiere")
                    .get(
                        niveau=classe.niveau,
                        matiere=matiere,
                        actif=True,
                        matiere__actif=True,
                        section=(
                            classe.section
                            if classe.section_id
                            else None
                        ),
                    )
                )

                affectation_matiere = (
                    AffectationMatiere.objects.create(
                        classe=classe,
                        matiere=matiere,
                        heures_par_semaine=(
                            ponderation.travaux_journaliers_max
                        ),
                    )
                )

            except PonderationMatiere.DoesNotExist:

                self.add_error(
                    "matiere",
                    (
                        "Cette matière n'est pas attribuée "
                        "à la classe sélectionnée."
                    )
                )

                return cleaned_data


        # -----------------------------------------------------
        # UN SEUL ENSEIGNANT ACTIF À LA FOIS
        # -----------------------------------------------------

        affectation_active = (
            Affectation.objects.filter(
                affectation_matiere=
                affectation_matiere,
                actif=True,
            )
        )


        # -----------------------------------------------------
        # EN MODIFICATION, ON EXCLUT L'AFFECTATION ACTUELLE
        # -----------------------------------------------------

        if self.instance.pk:

            affectation_active = (
                affectation_active.exclude(
                    pk=self.instance.pk
                )
            )


        # -----------------------------------------------------
        # VÉRIFICATION
        # -----------------------------------------------------

        if affectation_active.exists():

            autre_affectation = (
                affectation_active
                .select_related(
                    "enseignant__utilisateur"
                )
                .first()
            )


            self.add_error(
                "matiere",
                (
                    "Cette matière est déjà attribuée à "
                    f"{autre_affectation.enseignant} "
                    "pour cette classe."
                )
            )

            return cleaned_data


        # -----------------------------------------------------
        # CONSERVATION DE L'AFFECTATION MATIÈRE
        # -----------------------------------------------------

        cleaned_data[
            "affectation_matiere"
        ] = affectation_matiere


        return cleaned_data


    # =========================================================
    # ENREGISTREMENT
    # =========================================================

    def save(self, commit=True):

        affectation = super().save(
            commit=False
        )


        # -----------------------------------------------------
        # ASSOCIATION AVEC AFFECTATION MATIÈRE
        # -----------------------------------------------------

        affectation.affectation_matiere = (
            self.cleaned_data[
                "affectation_matiere"
            ]
        )


        # -----------------------------------------------------
        # ENREGISTREMENT
        # -----------------------------------------------------

        if commit:

            affectation.save()

        return affectation

    class Meta:

        model = Affectation


        fields = [
            "enseignant",
        ]

class ConfigurationHoraireForm(forms.ModelForm):

    # =========================================================
    # INITIALISATION
    # =========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # -----------------------------------------------------
        # ANNÉE SCOLAIRE
        # -----------------------------------------------------

        self.fields["annee"].queryset = (
            AnneeScolaire.objects.order_by(
                "-date_debut"
            )
        )

        self.fields["annee"].empty_label = (
            "Sélectionnez une année scolaire"
        )

        # -----------------------------------------------------
        # ATTRIBUTION DES CLASSES CSS
        # -----------------------------------------------------

        for field in self.fields.values():

            field.widget.attrs.update(
                {
                    "class": "form-control",
                }
            )

        # -----------------------------------------------------
        # CONFIGURATION VERROUILLÉE
        # -----------------------------------------------------

        # Si une configuration existante est verrouillée,
        # les champs deviennent non modifiables dans
        # l'interface.
        if (
            self.instance
            and self.instance.pk
            and self.instance.verrouillee
        ):

            for field in self.fields.values():

                field.widget.attrs.update(
                    {
                        "readonly": "readonly",
                    }
                )

                field.disabled = True


    # =========================================================
    # META
    # =========================================================

    class Meta:

        model = ConfigurationHoraire

        fields = [

            "annee",

            "heure_debut_journee",

            "duree_heure",

            "nombre_heures_par_jour",

            "pause_apres_heure",

            "duree_pause",

        ]

        widgets = {

            # -------------------------------------------------
            # ANNÉE SCOLAIRE
            # -------------------------------------------------

            "annee": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),


            # -------------------------------------------------
            # HEURE DE DÉBUT
            # -------------------------------------------------

            "heure_debut_journee": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),


            # -------------------------------------------------
            # DURÉE D'UNE HEURE
            # -------------------------------------------------

            "duree_heure": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": (
                        "Exemple : 50"
                    ),
                }
            ),


            # -------------------------------------------------
            # NOMBRE D'HEURES PAR JOUR
            # -------------------------------------------------

            "nombre_heures_par_jour": (
                forms.NumberInput(
                    attrs={
                        "class": "form-control",
                        "min": "2",
                        "placeholder": (
                            "Exemple : 6"
                        ),
                    }
                )
            ),


            # -------------------------------------------------
            # PAUSE APRÈS L'HEURE
            # -------------------------------------------------

            "pause_apres_heure": (
                forms.NumberInput(
                    attrs={
                        "class": "form-control",
                        "min": "1",
                        "placeholder": (
                            "Exemple : 3"
                        ),
                    }
                )
            ),


            # -------------------------------------------------
            # DURÉE DE LA PAUSE
            # -------------------------------------------------

            "duree_pause": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": (
                        "Exemple : 20"
                    ),
                }
            ),

        }


        labels = {

            "annee": (
                "Année scolaire"
            ),

            "heure_debut_journee": (
                "Heure de début de la journée"
            ),

            "duree_heure": (
                "Durée d'une heure de cours"
            ),

            "nombre_heures_par_jour": (
                "Nombre d'heures de cours par jour"
            ),

            "pause_apres_heure": (
                "La pause intervient après l'heure"
            ),

            "duree_pause": (
                "Durée de la pause"
            ),

        }


    # =========================================================
    # VALIDATION DE L'ANNÉE SCOLAIRE
    # =========================================================

    def clean_annee(self):

        annee = self.cleaned_data.get(
            "annee"
        )

        if not annee:

            return annee

        # -----------------------------------------------------
        # Une seule configuration générale doit exister
        # pour une même année scolaire.
        # -----------------------------------------------------

        configurations = (
            ConfigurationHoraire.objects.filter(
                annee=annee
            )
        )

        # En modification, on exclut la configuration actuelle.
        if (
            self.instance
            and self.instance.pk
        ):

            configurations = (
                configurations.exclude(
                    pk=self.instance.pk
                )
            )

        if configurations.exists():

            raise forms.ValidationError(
                "Une configuration horaire existe déjà "
                "pour cette année scolaire."
            )

        return annee


    # =========================================================
    # VALIDATION GLOBALE
    # =========================================================

    def clean(self):

        cleaned_data = super().clean()

        # -----------------------------------------------------
        # PROTECTION D'UNE CONFIGURATION VERROUILLÉE
        # -----------------------------------------------------

        if (
            self.instance
            and self.instance.pk
            and self.instance.verrouillee
        ):

            raise forms.ValidationError(
                "Cette configuration est verrouillée et "
                "ne peut plus être modifiée."
            )


        # -----------------------------------------------------
        # RÉCUPÉRATION DES DONNÉES
        # -----------------------------------------------------

        nombre_heures = cleaned_data.get(
            "nombre_heures_par_jour"
        )

        pause_apres = cleaned_data.get(
            "pause_apres_heure"
        )

        duree_heure = cleaned_data.get(
            "duree_heure"
        )

        duree_pause = cleaned_data.get(
            "duree_pause"
        )


        # -----------------------------------------------------
        # DURÉE D'UNE HEURE
        # -----------------------------------------------------

        if (
            duree_heure is not None
            and duree_heure <= 0
        ):

            self.add_error(

                "duree_heure",

                (
                    "La durée d'une heure de cours "
                    "doit être supérieure à zéro."
                )

            )


        # -----------------------------------------------------
        # NOMBRE D'HEURES
        # -----------------------------------------------------

        if (
            nombre_heures is not None
            and nombre_heures < 2
        ):

            self.add_error(

                "nombre_heures_par_jour",

                (
                    "Une journée scolaire doit contenir "
                    "au moins deux heures de cours."
                )

            )


        # -----------------------------------------------------
        # DURÉE DE LA PAUSE
        # -----------------------------------------------------

        if (
            duree_pause is not None
            and duree_pause <= 0
        ):

            self.add_error(

                "duree_pause",

                (
                    "La durée de la pause doit être "
                    "supérieure à zéro."
                )

            )


        # -----------------------------------------------------
        # POSITION DE LA PAUSE
        # -----------------------------------------------------

        if (

            nombre_heures is not None

            and pause_apres is not None

        ):


            # La pause doit intervenir après au moins
            # une heure de cours.
            if pause_apres < 1:

                self.add_error(

                    "pause_apres_heure",

                    (
                        "La pause doit intervenir après "
                        "au moins une heure de cours."
                    )

                )


            # Il ne peut pas y avoir de pause après une heure
            # qui n'existe pas.
            elif pause_apres >= nombre_heures:

                self.add_error(

                    "pause_apres_heure",

                    (
                        "La pause doit intervenir avant "
                        "la dernière heure de cours."
                    )

                )


        return cleaned_data

class HoraireForm(forms.ModelForm):

    class Meta:

        model = Horaire

        fields = [
            "affectation",
            "salle",
        ]

        widgets = {
            "salle": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Salle (facultatif)",
                }
            ),
        }

    def __init__(
        self,
        *args,
        annee=None,
        classe=None,
        creneau=None,
        jour_semaine=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.annee = annee
        self.classe = classe
        self.creneau = creneau
        self.jour_semaine = jour_semaine

        self.fields["affectation"].label = (
            "Cours à affecter"
        )

        # =====================================================
        # AUCUNE AFFECTATION PAR DÉFAUT
        # =====================================================

        self.fields[
            "affectation"
        ].queryset = Affectation.objects.none()

        # =====================================================
        # RECHERCHE DES AFFECTATIONS
        # =====================================================

        if annee and classe:

            affectations = (
                Affectation.objects.filter(
                    actif=True,
                    affectation_matiere__actif=True,
                    affectation_matiere__classe=classe,
                    affectation_matiere__classe__annee=annee,
                )
                .select_related(
                    "enseignant",
                    "affectation_matiere",
                    "affectation_matiere__matiere",
                    "affectation_matiere__classe",
                )
                .order_by(
                    "affectation_matiere__matiere__libelle"
                )
            )

            # =================================================
            # ENSEIGNANTS DÉJÀ OCCUPÉS
            # =================================================

            enseignants_occupes = set()

            if creneau and jour_semaine:

                horaires_existants = Horaire.objects.filter(
                    annee=annee,
                    jour_semaine=jour_semaine,
                    creneau=creneau,
                    actif=True,
                ).select_related(
                    "affectation",
                    "affectation__enseignant",
                )

                enseignants_occupes = {
                    horaire.affectation.enseignant_id
                    for horaire in horaires_existants
                }

            # =================================================
            # EXCLUSION DES ENSEIGNANTS OCCUPÉS
            # =================================================

            if enseignants_occupes:

                affectations = affectations.exclude(
                    enseignant_id__in=enseignants_occupes
                )

            self.fields[
                "affectation"
            ].queryset = affectations

    # =========================================================
    # VALIDATION DE L'AFFECTATION
    # =========================================================

    def clean_affectation(self):

        affectation = self.cleaned_data.get(
            "affectation"
        )

        if not affectation:
            return affectation

        # -----------------------------------------------------
        # LA CLASSE DOIT CORRESPONDRE
        # -----------------------------------------------------

        if (
            self.classe
            and affectation.affectation_matiere.classe
            != self.classe
        ):

            raise forms.ValidationError(
                "Cette affectation ne correspond pas "
                "à la classe sélectionnée."
            )

        # -----------------------------------------------------
        # L'ENSEIGNANT NE DOIT PAS ÊTRE DÉJÀ OCCUPÉ
        # -----------------------------------------------------

        if (
            self.annee
            and self.creneau
            and self.jour_semaine
        ):

            conflit = Horaire.objects.filter(
                annee=self.annee,
                jour_semaine=self.jour_semaine,
                creneau=self.creneau,
                actif=True,
                affectation__enseignant_id=(
                    affectation.enseignant_id
                ),
            )

            # En cas de modification
            if self.instance.pk:

                conflit = conflit.exclude(
                    pk=self.instance.pk
                )

            if conflit.exists():

                raise forms.ValidationError(
                    (
                        "Cet enseignant est déjà affecté "
                        "à une autre classe pendant ce "
                        "créneau."
                    )
                )

        return affectation

    # =========================================================
    # ENREGISTREMENT
    # =========================================================

    def save(self, commit=True):

        horaire = super().save(
            commit=False
        )

        horaire.annee = self.annee
        horaire.classe = self.classe
        horaire.creneau = self.creneau
        horaire.jour_semaine = self.jour_semaine

        if commit:

            horaire.full_clean()

            horaire.save()

        return horaire
    
class RepartitionHoraireForm(forms.ModelForm):

    # =========================================================
    # ANNÉE SCOLAIRE
    # =========================================================
    annee = forms.ModelChoiceField(
        queryset=AnneeScolaire.objects.none(),
        required=True,
        label="Année scolaire",
        empty_label="Sélectionnez une année scolaire",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_annee",
            }
        ),
    )

    # =========================================================
    # CLASSE
    # =========================================================
    classe = forms.ModelChoiceField(
        queryset=Classe.objects.none(),
        required=True,
        label="Classe",
        empty_label="Sélectionnez une classe",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_classe",
            }
        ),
    )

    # =========================================================
    # MATIÈRE AFFECTÉE À LA CLASSE
    # =========================================================
    affectation_matiere = forms.ModelChoiceField(
        queryset=AffectationMatiere.objects.none(),
        required=True,
        label="Matière",
        empty_label="Sélectionnez une matière",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_affectation_matiere",
            }
        ),
    )

    # =========================================================
    # JOUR
    #
    # Le champ existe déjà dans RepartitionHoraire.
    # =========================================================
    jour = forms.ChoiceField(
        choices=RepartitionHoraire.JOUR_CHOICES,
        required=True,
        label="Jour",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_jour",
            }
        ),
    )

    # =========================================================
    # CRÉNEAU HORAIRE
    # =========================================================
    creneau = forms.ModelChoiceField(
        queryset=CreneauHoraire.objects.none(),
        required=True,
        label="Créneau horaire",
        empty_label="Sélectionnez un créneau",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_creneau",
            }
        ),
    )

    # =========================================================
    # CONFIGURATION
    # =========================================================
    class Meta:

        model = RepartitionHoraire

        fields = [
            "classe",
            "affectation_matiere",
            "jour",
            "creneau",
        ]

    # =========================================================
    # INITIALISATION
    # =========================================================
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # -----------------------------------------------------
        # ANNÉES SCOLAIRES
        # -----------------------------------------------------
        self.fields["annee"].queryset = (
            AnneeScolaire.objects
            .all()
            .order_by("-date_debut")
        )

        # -----------------------------------------------------
        # MODE POST / FORMULAIRE LIÉ
        # -----------------------------------------------------
        if self.is_bound:

            annee_id = self.data.get("annee")

            classe_id = self.data.get("classe")

            # -------------------------------------------------
            # CLASSES DE L'ANNÉE
            # -------------------------------------------------
            if annee_id:

                try:

                    self.fields["classe"].queryset = (
                        Classe.objects
                        .filter(
                            annee_id=annee_id,
                            actif=True,
                        )
                        .select_related(
                            "annee",
                            "niveau",
                            "section",
                        )
                        .order_by(
                            "niveau__ordre",
                            "code",
                        )
                    )

                except (
                    ValueError,
                    TypeError,
                ):
                    pass

            # -------------------------------------------------
            # MATIÈRES DE LA CLASSE
            # -------------------------------------------------
            if classe_id:

                try:

                    self.fields[
                        "affectation_matiere"
                    ].queryset = (
                        AffectationMatiere.objects
                        .filter(
                            classe_id=classe_id,
                            actif=True,
                        )
                        .select_related(
                            "matiere",
                            "classe",
                        )
                        .order_by(
                            "matiere__libelle"
                        )
                    )

                except (
                    ValueError,
                    TypeError,
                ):
                    pass

            # -------------------------------------------------
            # CRÉNEAUX DE COURS
            #
            # On exclut automatiquement les pauses.
            # -------------------------------------------------
            if annee_id:

                try:

                    self.fields["creneau"].queryset = (
                        CreneauHoraire.objects
                        .filter(
                            configuration__annee_id=annee_id,
                            type_creneau=(
                                CreneauHoraire.TYPE_COURS
                            ),
                            actif=True,
                        )
                        .select_related(
                            "configuration",
                        )
                        .order_by(
                            "ordre"
                        )
                    )

                except (
                    ValueError,
                    TypeError,
                ):
                    pass

        # =====================================================
        # MODE MODIFICATION
        # =====================================================
        elif self.instance.pk:

            repartition = self.instance

            # -------------------------------------------------
            # ANNÉE
            # -------------------------------------------------
            annee = repartition.classe.annee

            self.fields["annee"].initial = annee

            # -------------------------------------------------
            # CLASSE
            # -------------------------------------------------
            self.fields["classe"].queryset = (
                Classe.objects
                .filter(
                    annee=annee,
                    actif=True,
                )
                .select_related(
                    "annee",
                    "niveau",
                    "section",
                )
                .order_by(
                    "niveau__ordre",
                    "code",
                )
            )

            self.fields["classe"].initial = (
                repartition.classe
            )

            # -------------------------------------------------
            # MATIÈRES
            # -------------------------------------------------
            self.fields[
                "affectation_matiere"
            ].queryset = (
                AffectationMatiere.objects
                .filter(
                    classe=repartition.classe,
                    actif=True,
                )
                .select_related(
                    "matiere",
                )
                .order_by(
                    "matiere__libelle"
                )
            )

            self.fields[
                "affectation_matiere"
            ].initial = (
                repartition.affectation_matiere
            )

            # -------------------------------------------------
            # CRÉNEAUX
            # -------------------------------------------------
            self.fields["creneau"].queryset = (
                CreneauHoraire.objects
                .filter(
                    configuration__annee=annee,
                    type_creneau=(
                        CreneauHoraire.TYPE_COURS
                    ),
                    actif=True,
                )
                .order_by(
                    "ordre"
                )
            )

            self.fields["creneau"].initial = (
                repartition.creneau
            )

    # =========================================================
    # VALIDATION
    # =========================================================
    def clean(self):

        cleaned_data = super().clean()

        annee = cleaned_data.get(
            "annee"
        )

        classe = cleaned_data.get(
            "classe"
        )

        affectation_matiere = cleaned_data.get(
            "affectation_matiere"
        )

        jour = cleaned_data.get(
            "jour"
        )

        creneau = cleaned_data.get(
            "creneau"
        )

        # -----------------------------------------------------
        # INFORMATIONS INCOMPLÈTES
        # -----------------------------------------------------
        if not all([
            annee,
            classe,
            affectation_matiere,
            jour,
            creneau,
        ]):

            return cleaned_data

        # -----------------------------------------------------
        # LA CLASSE DOIT APPARTENIR À L'ANNÉE
        # -----------------------------------------------------
        if classe.annee_id != annee.id:

            self.add_error(
                "classe",
                (
                    "La classe sélectionnée "
                    "n'appartient pas à cette année scolaire."
                )
            )

            return cleaned_data

        # -----------------------------------------------------
        # LA MATIÈRE DOIT APPARTENIR À LA CLASSE
        # -----------------------------------------------------
        if affectation_matiere.classe_id != classe.id:

            self.add_error(
                "affectation_matiere",
                (
                    "Cette matière n'est pas affectée "
                    "à la classe sélectionnée."
                )
            )

            return cleaned_data

        # -----------------------------------------------------
        # LE CRÉNEAU DOIT APPARTENIR À L'ANNÉE
        # -----------------------------------------------------
        if (
            creneau.configuration.annee_id
            != annee.id
        ):

            self.add_error(
                "creneau",
                (
                    "Ce créneau n'appartient pas "
                    "à l'année scolaire sélectionnée."
                )
            )

            return cleaned_data

        # -----------------------------------------------------
        # UNE PAUSE NE PEUT PAS ÊTRE UTILISÉE
        # -----------------------------------------------------
        if (
            creneau.type_creneau
            != CreneauHoraire.TYPE_COURS
        ):

            self.add_error(
                "creneau",
                (
                    "Seuls les créneaux de cours "
                    "peuvent être utilisés."
                )
            )

            return cleaned_data

        return cleaned_data


class EleveForm(forms.ModelForm):

    class Meta:
        model = Eleve
        fields = [
            "nom",
            "postnom",
            "prenom",
            "sexe",
            "date_naissance",
            "lieu_naissance",
            "adresse",
            "telephone",
            "email",
            "photo",
        ]
        widgets = {
            "nom": forms.TextInput(
                attrs={"placeholder": "Nom"}
            ),
            "postnom": forms.TextInput(
                attrs={"placeholder": "Postnom"}
            ),
            "prenom": forms.TextInput(
                attrs={"placeholder": "Prénom"}
            ),
            "sexe": forms.Select(
                attrs={"placeholder": "Sexe"}
            ),
            "date_naissance": forms.DateInput(
                attrs={"type": "date"},
            ),
            "lieu_naissance": forms.TextInput(
                attrs={"placeholder": "Lieu de naissance"}
            ),
            "adresse": forms.TextInput(
                attrs={"placeholder": "Adresse"}
            ),
            "telephone": forms.TextInput(
                attrs={"placeholder": "Téléphone"}
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": "Email"}
            ),
            "photo": forms.FileInput(),
        }


class InscriptionForm(forms.ModelForm):

    class Meta:
        model = Inscription
        fields = [
            "eleve",
            "classe",
            "annee",
            "type_inscription",
        ]
        widgets = {
            "eleve": forms.Select(),
            "classe": forms.Select(),
            "annee": forms.Select(),
            "type_inscription": forms.Select(),
        }


class FraisScolairesForm(forms.ModelForm):

    class Meta:
        model = FraisScolaires
        fields = [
            "annee",
            "libelle",
            "montant_total",
            "actif",
        ]
        widgets = {
            "annee": forms.Select(attrs={"class": "form-control"}),
            "libelle": forms.TextInput(attrs={"class": "form-control", "placeholder": "Libellé des frais"}),
            "montant_total": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TrancheForm(forms.ModelForm):

    class Meta:
        model = Tranche
        fields = [
            "frais",
            "numero",
            "montant",
            "date_echeance",
        ]
        widgets = {
            "frais": forms.Select(attrs={"class": "form-control"}),
            "numero": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "montant": forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01"}),
            "date_echeance": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class ModeleBulletinForm(forms.ModelForm):

    class Meta:
        model = ModeleBulletin
        fields = [
            "libelle",
            "version",
            "actif",
        ]
        widgets = {
            "libelle": forms.TextInput(attrs={"class": "form-control", "placeholder": "Libellé du modèle"}),
            "version": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: v1"}),
            "actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ResponsableLegalForm(forms.ModelForm):

    class Meta:
        model = ResponsableLegal
        fields = [
            "nom",
            "postnom",
            "prenom",
            "telephone",
            "email",
            "adresse",
            "profession",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom"}),
            "postnom": forms.TextInput(attrs={"class": "form-control", "placeholder": "Postnom"}),
            "prenom": forms.TextInput(attrs={"class": "form-control", "placeholder": "Prénom"}),
            "telephone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Téléphone"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "adresse": forms.TextInput(attrs={"class": "form-control", "placeholder": "Adresse"}),
            "profession": forms.TextInput(attrs={"class": "form-control", "placeholder": "Profession"}),
        }


class ResponsabiliteScolaireForm(forms.ModelForm):

    class Meta:
        model = ResponsabiliteScolaire
        fields = [
            "type_responsabilite",
            "principal",
            "autorise_notification",
        ]
        widgets = {
            "type_responsabilite": forms.Select(attrs={"class": "form-control"}),
            "principal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "autorise_notification": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TitularisationForm(forms.ModelForm):
    annee = forms.ModelChoiceField(
        queryset=AnneeScolaire.objects.none(),
        required=True,
        label="Année scolaire",
        empty_label="Sélectionnez une année scolaire",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_annee",
            }
        ),
    )

    classe = forms.ModelChoiceField(
        queryset=Classe.objects.none(),
        required=True,
        label="Classe",
        empty_label="Sélectionnez une classe",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_classe",
            }
        ),
    )

    enseignant = forms.ModelChoiceField(
        queryset=Enseignant.objects.none(),
        required=True,
        label="Enseignant",
        empty_label="Sélectionnez un enseignant",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_enseignant",
            }
        ),
    )

    class Meta:
        model = Titularisation
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["annee"].queryset = (
            AnneeScolaire.objects.all()
            .order_by("-date_debut")
        )

        # =========================================================
        # ANNÉE DE RÉFÉRENCE
        #
        # En modification : l'année de la titularisation.
        # En soumission : l'année envoyée avec le formulaire.
        # Sinon : aucune, l'utilisateur doit d'abord choisir.
        # =========================================================

        annee_reference = None

        if self.instance.pk:
            annee_reference = self.instance.annee_id

        if self.is_bound:
            annee_envoyee = self.data.get("annee")

            if annee_envoyee:
                try:
                    annee_reference = int(annee_envoyee)
                except (TypeError, ValueError):
                    annee_reference = None

        self.annee_reference = annee_reference

        self.fields["classe"].queryset = (
            self._classes_disponibles(annee_reference)
        )

        self.fields["enseignant"].queryset = (
            self._enseignants_disponibles(annee_reference)
        )

        self.fields["annee"].empty_label = (
            "Sélectionnez une année scolaire"
        )
        self.fields["classe"].empty_label = (
            "Sélectionnez une classe"
        )
        self.fields["enseignant"].empty_label = (
            "Sélectionnez un enseignant"
        )

    def _classes_disponibles(self, annee_id):
        """
        Classes de l'année scolaire qui n'ont pas encore
        de titulaire actif.
        """

        if not annee_id:
            return Classe.objects.none()

        classes_titulaires = Titularisation.objects.filter(
            annee_id=annee_id,
            statut=Titularisation.ACTIVE,
        ).values_list("classe_id", flat=True)

        return (
            Classe.objects
            .filter(
                annee_id=annee_id,
                actif=True,
            )
            .exclude(id__in=classes_titulaires)
            .select_related("annee", "niveau", "section")
            .order_by("niveau__ordre", "code")
        )

    def _enseignants_disponibles(self, annee_id):
        """
        Enseignants actifs qui ne sont pas déjà titulaires
        d'une classe pour l'année scolaire donnée.
        """

        if not annee_id:
            return Enseignant.objects.none()

        enseignants_titulaires = Titularisation.objects.filter(
            annee_id=annee_id,
            statut=Titularisation.ACTIVE,
        ).values_list("enseignant_id", flat=True)

        return (
            Enseignant.objects
            .filter(
                actif=True,
                utilisateur__actif=True,
            )
            .exclude(id__in=enseignants_titulaires)
            .select_related("utilisateur")
            .order_by(
                "utilisateur__nom",
                "utilisateur__prenom",
            )
        )

    def _post_clean(self):
        """
        Les clés étrangères sont déclarées comme champs de
        formulaire et non comme champs du modèle.

        Comme Meta.fields est vide, Django ne les assigne pas
        automatiquement à l'instance avant d'appeler
        full_clean(), ce qui produit une erreur de type
        "Ce champ ne peut pas contenir la valeur nulle".

        On les assigne donc explicitement avant la validation.
        """

        annee = self.cleaned_data.get("annee")

        classe = self.cleaned_data.get("classe")

        enseignant = self.cleaned_data.get("enseignant")

        if annee is not None:
            self.instance.annee = annee

        if classe is not None:
            self.instance.classe = classe

        if enseignant is not None:
            self.instance.enseignant = enseignant

        if self.instance.annee_id and self.instance.classe_id:
            self.instance.statut = Titularisation.ACTIVE

        super()._post_clean()

    def clean(self):
        cleaned_data = super().clean()

        annee = cleaned_data.get("annee")
        classe = cleaned_data.get("classe")
        enseignant = cleaned_data.get("enseignant")

        if not all([annee, classe, enseignant]):
            return cleaned_data

        if classe.annee_id != annee.id:
            self.add_error(
                "classe",
                "La classe sélectionnée n'appartient pas à l'année scolaire choisie."
            )

        # Vérifier si la classe a déjà un titulaire
        if Titularisation.objects.filter(
            classe=classe,
            annee=annee,
            statut=Titularisation.ACTIVE,
        ).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
            self.add_error(
                "classe",
                "Cette classe possède déjà un titulaire pour cette année scolaire."
            )

        # Vérifier si l'enseignant est déjà titulaire d'une autre classe
        if Titularisation.objects.filter(
            enseignant=enseignant,
            annee=annee,
            statut=Titularisation.ACTIVE,
        ).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
            self.add_error(
                "enseignant",
                "Cet enseignant est déjà titulaire d'une autre classe pour cette année scolaire."
            )

        return cleaned_data

    def save(self, commit=True):
        titularisation = super().save(commit=False)

        titularisation.annee = self.cleaned_data["annee"]
        titularisation.classe = self.cleaned_data["classe"]
        titularisation.enseignant = self.cleaned_data["enseignant"]
        titularisation.statut = Titularisation.ACTIVE

        if commit:
            titularisation.save()

        return titularisation


# ============================================================
# INSCRIPTION COMPLETE (ELEVE + RESPONSABLES + INSCRIPTION)
# ============================================================

TEXT_CSS = {"class": "form-control"}
SELECT_CSS = {"class": "form-select"}


class InscriptionCompleteForm(forms.Form):
    """Formulaire unique d'inscription scolaire.

    Regroupe sur une seule page :
    - l'identite de l'eleve (nouveau ou deja existant) ;
    - un responsable legal obligatoire (parent/tuteur) ;
    - un second responsable legal facultatif ;
    - les informations d'inscription (annee, classe, type).

    Le save() cree l'eleve, les responsables, les liens de responsabilite
    et l'inscription dans une seule transaction.
    """

    # ---------------------------------------------------------
    # ELEVE
    # ---------------------------------------------------------
    mode_eleve = forms.ChoiceField(
        choices=[
            ("nouveau", "Inscrire un nouvel élève"),
            ("existant", "Inscrire un élève déjà enregistré"),
        ],
        initial="nouveau",
        widget=forms.RadioSelect(attrs=SELECT_CSS),
        label="Élève",
    )

    eleve_id = forms.ModelChoiceField(
        queryset=Eleve.objects.none(),
        required=False,
        label="Élève existant",
        empty_label="— Sélectionner un élève —",
        widget=forms.Select(attrs=SELECT_CSS),
    )

    matricule = forms.CharField(
        required=False,
        max_length=50,
        label="Matricule",
        widget=forms.TextInput(
            attrs={
                **TEXT_CSS,
                "placeholder": "Généré automatiquement si laissé vide",
            }
        ),
        help_text="Laissez vide pour générer automatiquement.",
    )

    eleve_nom = forms.CharField(
        required=False,
        max_length=80,
        label="Nom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Nom"}),
    )

    eleve_postnom = forms.CharField(
        required=False,
        max_length=80,
        label="Postnom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Postnom"}),
    )

    eleve_prenom = forms.CharField(
        required=False,
        max_length=80,
        label="Prénom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Prénom"}),
    )

    eleve_sexe = forms.ChoiceField(
        required=False,
        choices=[("", "— Sélectionner —"), ("M", "Masculin"), ("F", "Féminin")],
        label="Sexe",
        widget=forms.Select(attrs=SELECT_CSS),
    )

    eleve_date_naissance = forms.DateField(
        required=False,
        label="Date de naissance",
        widget=forms.DateInput(attrs={**TEXT_CSS, "type": "date"}),
    )

    eleve_lieu_naissance = forms.CharField(
        required=False,
        max_length=150,
        label="Lieu de naissance",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Lieu de naissance"}),
    )

    eleve_adresse = forms.CharField(
        required=False,
        max_length=255,
        label="Adresse",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Adresse de résidence"}),
    )

    eleve_telephone = forms.CharField(
        required=False,
        max_length=30,
        label="Téléphone",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Téléphone"}),
    )

    eleve_email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={**TEXT_CSS, "placeholder": "Email"}),
    )

    eleve_photo = forms.FileField(
        required=False,
        label="Photo",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )

    # ---------------------------------------------------------
    # RESPONSABLE LEGAL
    # ---------------------------------------------------------
    resp_type_responsabilite = forms.ChoiceField(
        choices=[
            ("PERE", "Père"),
            ("MERE", "Mère"),
            ("TUTEUR", "Tuteur"),
            ("AUTRE", "Autre"),
        ],
        initial="PERE",
        widget=forms.Select(attrs=SELECT_CSS),
        label="Lien avec l'élève",
    )

    resp_nom = forms.CharField(
        max_length=80,
        label="Nom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Nom"}),
    )

    resp_postnom = forms.CharField(
        required=False,
        max_length=80,
        label="Postnom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Postnom"}),
    )

    resp_prenom = forms.CharField(
        max_length=80,
        label="Prénom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Prénom"}),
    )

    resp_telephone = forms.CharField(
        max_length=30,
        label="Téléphone",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Téléphone (obligatoire)"}),
    )

    resp_email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={**TEXT_CSS, "placeholder": "Email"}),
    )

    resp_adresse = forms.CharField(
        required=False,
        max_length=255,
        label="Adresse",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Adresse"}),
    )

    resp_profession = forms.CharField(
        required=False,
        max_length=100,
        label="Profession",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Profession"}),
    )

    resp_principal = forms.BooleanField(
        initial=True,
        required=False,
        label="Responsable principal",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Le responsable principal reçoit les notifications en priorité.",
    )

    # ---------------------------------------------------------
    # SECOND RESPONSABLE (FACULTATIF)
    # ---------------------------------------------------------
    resp2_actif = forms.BooleanField(
        required=False,
        initial=False,
        label="Ajouter un second responsable",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    resp2_type_responsabilite = forms.ChoiceField(
        required=False,
        choices=[
            ("", "— Sélectionner —"),
            ("PERE", "Père"),
            ("MERE", "Mère"),
            ("TUTEUR", "Tuteur"),
            ("AUTRE", "Autre"),
        ],
        widget=forms.Select(attrs=SELECT_CSS),
        label="Lien avec l'élève",
    )

    resp2_nom = forms.CharField(
        required=False,
        max_length=80,
        label="Nom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Nom"}),
    )

    resp2_postnom = forms.CharField(
        required=False,
        max_length=80,
        label="Postnom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Postnom"}),
    )

    resp2_prenom = forms.CharField(
        required=False,
        max_length=80,
        label="Prénom",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Prénom"}),
    )

    resp2_telephone = forms.CharField(
        required=False,
        max_length=30,
        label="Téléphone",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Téléphone"}),
    )

    resp2_email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={**TEXT_CSS, "placeholder": "Email"}),
    )

    resp2_adresse = forms.CharField(
        required=False,
        max_length=255,
        label="Adresse",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Adresse"}),
    )

    resp2_profession = forms.CharField(
        required=False,
        max_length=100,
        label="Profession",
        widget=forms.TextInput(attrs={**TEXT_CSS, "placeholder": "Profession"}),
    )

    # ---------------------------------------------------------
    # INSCRIPTION
    # ---------------------------------------------------------
    annee = forms.ModelChoiceField(
        queryset=AnneeScolaire.objects.none(),
        label="Année scolaire",
        empty_label="— Sélectionner une année —",
        widget=forms.Select(attrs=SELECT_CSS),
    )

    classe = forms.ModelChoiceField(
        queryset=Classe.objects.none(),
        label="Classe",
        empty_label="— Sélectionner une classe —",
        widget=forms.Select(attrs=SELECT_CSS),
    )

    type_inscription = forms.ChoiceField(
        choices=[
            (Inscription.NOUVELLE, "Nouvelle inscription"),
            (Inscription.REINSCRIPTION, "Réinscription"),
        ],
        initial=Inscription.NOUVELLE,
        widget=forms.Select(attrs=SELECT_CSS),
        label="Type d'inscription",
    )

    bulletin_precedent_verifie = forms.BooleanField(
        required=False,
        initial=False,
        label="Bulletin de l'année précédente vérifié",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Obligatoire pour une réinscription.",
    )

    # ---------------------------------------------------------
    def __init__(self, *args, eleve=None, **kwargs):
        # `eleve` active le mode edition : les donnees existantes sont
        # pre-remplies et save() met a jour au lieu de creer.
        self.eleve = eleve
        super().__init__(*args, **kwargs)

        self.fields["eleve_id"].queryset = (
            Eleve.objects.filter(actif=True).order_by("nom", "prenom")
        )
        self.fields["annee"].queryset = (
            AnneeScolaire.objects.all().order_by("-id")
        )

        # Liste des classes restreinte a l'annee choisie (champ lie)
        if self.is_bound:
            annee_id = self.data.get("annee")
            if annee_id:
                try:
                    self.fields["classe"].queryset = Classe.objects.filter(
                        annee_id=annee_id, actif=True
                    ).order_by("libelle")
                except (ValueError, TypeError):
                    pass

        if self.eleve is not None:
            self._initialiser_edition(self.eleve)

    def _initialiser_edition(self, eleve):
        """Pre-remplit le formulaire avec les donnees d'un eleve existant."""
        self.initial["mode_eleve"] = "existant"
        self.initial["eleve_id"] = eleve
        self.initial["matricule"] = eleve.matricule
        self.initial["eleve_nom"] = eleve.nom
        self.initial["eleve_postnom"] = eleve.postnom or ""
        self.initial["eleve_prenom"] = eleve.prenom
        self.initial["eleve_sexe"] = eleve.sexe or ""
        self.initial["eleve_date_naissance"] = eleve.date_naissance
        self.initial["eleve_lieu_naissance"] = eleve.lieu_naissance or ""
        self.initial["eleve_adresse"] = eleve.adresse or ""
        self.initial["eleve_telephone"] = eleve.telephone or ""
        self.initial["eleve_email"] = eleve.email or ""

        # Le matricule est fige : c'est l'identifiant de l'eleve.
        self.fields["matricule"].disabled = True
        self.fields["eleve_id"].disabled = True
        self.fields["eleve_id"].widget = forms.HiddenInput()
        self.fields["mode_eleve"].widget = forms.HiddenInput()

        # Responsables deja rattaches
        responsabilites = list(
            ResponsabiliteScolaire.objects
            .filter(eleve=eleve)
            .select_related("responsable")
            .order_by("-principal", "id")
        )

        if responsabilites:
            principal = responsabilites[0]
            self.initial["resp_type_responsabilite"] = principal.type_responsabilite
            self.initial["resp_nom"] = principal.responsable.nom
            self.initial["resp_postnom"] = principal.responsable.postnom or ""
            self.initial["resp_prenom"] = principal.responsable.prenom
            self.initial["resp_telephone"] = principal.responsable.telephone or ""
            self.initial["resp_email"] = principal.responsable.email or ""
            self.initial["resp_adresse"] = principal.responsable.adresse or ""
            self.initial["resp_profession"] = principal.responsable.profession or ""

        if len(responsabilites) > 1:
            secondaire = responsabilites[1]
            self.initial["resp2_actif"] = True
            self.initial["resp2_type_responsabilite"] = (
                secondaire.type_responsabilite
            )
            self.initial["resp2_nom"] = secondaire.responsable.nom
            self.initial["resp2_postnom"] = secondaire.responsable.postnom or ""
            self.initial["resp2_prenom"] = secondaire.responsable.prenom
            self.initial["resp2_telephone"] = (
                secondaire.responsable.telephone or ""
            )
            self.initial["resp2_email"] = secondaire.responsable.email or ""
            self.initial["resp2_adresse"] = secondaire.responsable.adresse or ""
            self.initial["resp2_profession"] = (
                secondaire.responsable.profession or ""
            )

        # Inscription en cours pour cet eleve
        inscription = (
            Inscription.objects
            .filter(eleve=eleve, statut=Inscription.ACTIVE)
            .select_related("annee", "classe")
            .order_by("-annee__date_debut")
            .first()
        )
        if inscription:
            self.initial["annee"] = inscription.annee
            self.initial["classe"] = inscription.classe
            self.initial["type_inscription"] = inscription.type_inscription
            self.fields["classe"].queryset = Classe.objects.filter(
                annee=inscription.annee, actif=True
            ).order_by("libelle")

    def clean(self):
        cleaned_data = super().clean()
        mode_eleve = cleaned_data.get("mode_eleve")
        annee = cleaned_data.get("annee")
        classe = cleaned_data.get("classe")
        type_inscription = cleaned_data.get("type_inscription")
        bulletin_verifie = cleaned_data.get("bulletin_precedent_verifie")

        # --- coherence annee / classe -----------------------------
        if annee and classe and classe.annee_id != annee.id:
            self.add_error(
                "classe",
                "La classe sélectionnée n'appartient pas à l'année scolaire choisie.",
            )

        # --- identite de l'eleve ---------------------------------
        if mode_eleve == "existant":
            # En edition le champ est desactive : l'eleve vient de self.eleve
            if not cleaned_data.get("eleve_id") and self.eleve is None:
                self.add_error(
                    "eleve_id",
                    "Sélectionnez l'élève déjà enregistré.",
                )
            elif annee and self.eleve is None:
                # En edition l'eleve est deja inscrit : on n'applique pas
                # le controle de doublon d'inscription.
                deja_inscrit = Inscription.objects.filter(
                    eleve=cleaned_data["eleve_id"],
                    annee=annee,
                ).exists()
                if deja_inscrit:
                    self.add_error(
                        "eleve_id",
                        "Cet élève est déjà inscrit pour cette année scolaire.",
                    )
        else:
            # Nouvel eleve ou edition : nom et prenom obligatoires
            for champ in ("eleve_nom", "eleve_prenom"):
                if not cleaned_data.get(champ):
                    self.add_error(champ, "Ce champ est obligatoire.")

            matricule = (cleaned_data.get("matricule") or "").strip()
            if (
                mode_eleve == "nouveau"
                and self.eleve is None
                and matricule
                and Eleve.objects.filter(matricule=matricule).exists()
            ):
                self.add_error(
                    "matricule",
                    "Ce matricule est déjà utilisé par un autre élève.",
                )

        # --- responsable principal obligatoire --------------------
        if not cleaned_data.get("resp_nom"):
            self.add_error("resp_nom", "Le nom du responsable est obligatoire.")
        if not cleaned_data.get("resp_prenom"):
            self.add_error("resp_prenom", "Le prénom du responsable est obligatoire.")

        # --- second responsable ----------------------------------
        if cleaned_data.get("resp2_actif"):
            for champ in ("resp2_nom", "resp2_prenom"):
                if not cleaned_data.get(champ):
                    self.add_error(
                        champ,
                        "Ce champ est obligatoire pour le second responsable.",
                    )
            if not cleaned_data.get("resp2_type_responsabilite"):
                self.add_error(
                    "resp2_type_responsabilite",
                    "Précisez le lien avec l'élève.",
                )
            if cleaned_data.get("resp2_nom") and (
                cleaned_data.get("resp2_nom", "").strip().lower()
                == cleaned_data.get("resp_nom", "").strip().lower()
                and cleaned_data.get("resp2_prenom", "").strip().lower()
                == cleaned_data.get("resp_prenom", "").strip().lower()
            ):
                self.add_error(
                    "resp2_nom",
                    "Le second responsable doit être une personne différente.",
                )

        # --- regles de reinscription ------------------------------
        if type_inscription == Inscription.REINSCRIPTION and not bulletin_verifie:
            self.add_error(
                "bulletin_precedent_verifie",
                "Une réinscription exige la vérification du bulletin "
                "de l'année précédente.",
            )

        return cleaned_data

    # ---------------------------------------------------------
    def _creer_responsable(self, prefixe, principal):
        """Cree un responsable legal a partir des champs prefixes."""
        donnees = {
            "nom": (self.cleaned_data.get(f"{prefixe}nom") or "").strip(),
            "prenom": (self.cleaned_data.get(f"{prefixe}prenom") or "").strip(),
            "postnom": (self.cleaned_data.get(f"{prefixe}postnom") or "").strip() or None,
            "telephone": (self.cleaned_data.get(f"{prefixe}telephone") or "").strip(),
            "email": (self.cleaned_data.get(f"{prefixe}email") or "").strip() or None,
            "adresse": (self.cleaned_data.get(f"{prefixe}adresse") or "").strip() or None,
            "profession": (self.cleaned_data.get(f"{prefixe}profession") or "").strip() or None,
        }
        return ResponsableLegal.objects.create(**donnees)

    # ---------------------------------------------------------
    def _appliquer_donnees_responsable(self, responsable, prefixe):
        """Ecrit les champs prefixes sur un responsable existant."""
        responsable.nom = (self.cleaned_data.get(f"{prefixe}nom") or "").strip()
        responsable.prenom = (
            self.cleaned_data.get(f"{prefixe}prenom") or ""
        ).strip()
        responsable.postnom = (
            self.cleaned_data.get(f"{prefixe}postnom") or ""
        ).strip() or None
        responsable.telephone = (
            self.cleaned_data.get(f"{prefixe}telephone") or ""
        ).strip()
        responsable.email = (
            self.cleaned_data.get(f"{prefixe}email") or ""
        ).strip() or None
        responsable.adresse = (
            self.cleaned_data.get(f"{prefixe}adresse") or ""
        ).strip() or None
        responsable.profession = (
            self.cleaned_data.get(f"{prefixe}profession") or ""
        ).strip() or None
        responsable.save()
        return responsable

    def _responsables_existants(self, eleve):
        """Responsabilites de l'eleve, la principale en premier."""
        return list(
            ResponsabiliteScolaire.objects
            .filter(eleve=eleve)
            .select_related("responsable")
            .order_by("-principal", "id")
        )

    def save(self, commit=True):
        from django.db import transaction

        if not self.is_valid():
            raise ValueError("Le formulaire doit être valide avant save().")

        with transaction.atomic():
            # ==================================================
            # MODE EDITION : mise a jour de l'eleve existant
            # ==================================================
            if self.eleve is not None:
                eleve = self.eleve
                eleve.nom = (
                    self.cleaned_data.get("eleve_nom") or ""
                ).strip()
                eleve.postnom = (
                    self.cleaned_data.get("eleve_postnom") or ""
                ).strip() or None
                eleve.prenom = (
                    self.cleaned_data.get("eleve_prenom") or ""
                ).strip()
                eleve.sexe = self.cleaned_data.get("eleve_sexe") or None
                eleve.date_naissance = self.cleaned_data.get(
                    "eleve_date_naissance"
                )
                eleve.lieu_naissance = (
                    self.cleaned_data.get("eleve_lieu_naissance") or ""
                ).strip() or None
                eleve.adresse = (
                    self.cleaned_data.get("eleve_adresse") or ""
                ).strip() or None
                eleve.telephone = (
                    self.cleaned_data.get("eleve_telephone") or ""
                ).strip() or None
                eleve.email = (
                    self.cleaned_data.get("eleve_email") or ""
                ).strip() or None

                photo = self.cleaned_data.get("eleve_photo")
                if photo:
                    eleve.photo = photo
                eleve.save()

                # Responsable principal : met a jour ou cree
                responsabilites = self._responsables_existants(eleve)

                if responsabilites:
                    lien_principal = responsabilites[0]
                    self._appliquer_donnees_responsable(
                        lien_principal.responsable, "resp_"
                    )
                    lien_principal.type_responsabilite = self.cleaned_data[
                        "resp_type_responsabilite"
                    ]
                    lien_principal.principal = True
                    lien_principal.save()
                else:
                    responsable = self._creer_responsable("resp_", True)
                    ResponsabiliteScolaire.objects.create(
                        eleve=eleve,
                        responsable=responsable,
                        type_responsabilite=self.cleaned_data[
                            "resp_type_responsabilite"
                        ],
                        principal=True,
                        autorise_notification=True,
                    )

                # Second responsable
                if self.cleaned_data.get("resp2_actif"):
                    if len(responsabilites) > 1:
                        lien_second = responsabilites[1]
                        self._appliquer_donnees_responsable(
                            lien_second.responsable, "resp2_"
                        )
                        lien_second.type_responsabilite = self.cleaned_data[
                            "resp2_type_responsabilite"
                        ]
                        lien_second.principal = False
                        lien_second.save()
                    else:
                        responsable_2 = self._creer_responsable("resp2_", False)
                        ResponsabiliteScolaire.objects.create(
                            eleve=eleve,
                            responsable=responsable_2,
                            type_responsabilite=self.cleaned_data[
                                "resp2_type_responsabilite"
                            ],
                            principal=False,
                            autorise_notification=True,
                        )
                elif len(responsabilites) > 1:
                    # Le second responsable a ete retire du formulaire
                    responsabilites[1].delete()

                # Inscription : mise a jour si elle existe pour l'annee
                inscription = (
                    Inscription.objects
                    .filter(eleve=eleve, annee=self.cleaned_data["annee"])
                    .first()
                )
                if inscription is None:
                    inscription = Inscription.objects.create(
                        eleve=eleve,
                        annee=self.cleaned_data["annee"],
                        classe=self.cleaned_data["classe"],
                        type_inscription=self.cleaned_data["type_inscription"],
                        bulletin_precedent_verifie=self.cleaned_data.get(
                            "bulletin_precedent_verifie", False
                        ),
                        statut=Inscription.ACTIVE,
                    )
                else:
                    inscription.classe = self.cleaned_data["classe"]
                    inscription.type_inscription = self.cleaned_data[
                        "type_inscription"
                    ]
                    inscription.bulletin_precedent_verifie = (
                        self.cleaned_data.get("bulletin_precedent_verifie", False)
                    )
                    inscription.save()

                return inscription

            # ==================================================
            # MODE CREATION
            # ==================================================
            if self.cleaned_data["mode_eleve"] == "existant":
                eleve = self.cleaned_data["eleve_id"]
            else:
                annee = self.cleaned_data["annee"]
                classe = self.cleaned_data["classe"]
                matricule = (self.cleaned_data.get("matricule") or "").strip()
                if not matricule:
                    matricule = Eleve.generer_matricule(classe)

                eleve = Eleve.objects.create(
                    matricule=matricule,
                    nom=(self.cleaned_data.get("eleve_nom") or "").strip(),
                    postnom=(self.cleaned_data.get("eleve_postnom") or "").strip() or None,
                    prenom=(self.cleaned_data.get("eleve_prenom") or "").strip(),
                    sexe=self.cleaned_data.get("eleve_sexe") or None,
                    date_naissance=self.cleaned_data.get("eleve_date_naissance"),
                    lieu_naissance=(self.cleaned_data.get("eleve_lieu_naissance") or "").strip() or None,
                    adresse=(self.cleaned_data.get("eleve_adresse") or "").strip() or None,
                    telephone=(self.cleaned_data.get("eleve_telephone") or "").strip() or None,
                    email=(self.cleaned_data.get("eleve_email") or "").strip() or None,
                    photo=self.cleaned_data.get("eleve_photo"),
                )

            # 2. Responsable principal
            responsable_principal = self._creer_responsable("resp_", True)
            ResponsabiliteScolaire.objects.create(
                eleve=eleve,
                responsable=responsable_principal,
                type_responsabilite=self.cleaned_data["resp_type_responsabilite"],
                principal=True,
                autorise_notification=True,
            )

            # 3. Second responsable (facultatif)
            if self.cleaned_data.get("resp2_actif"):
                responsable_2 = self._creer_responsable("resp2_", False)
                ResponsabiliteScolaire.objects.create(
                    eleve=eleve,
                    responsable=responsable_2,
                    type_responsabilite=self.cleaned_data["resp2_type_responsabilite"],
                    principal=False,
                    autorise_notification=True,
                )

            # 4. Inscription
            inscription = Inscription.objects.create(
                eleve=eleve,
                annee=self.cleaned_data["annee"],
                classe=self.cleaned_data["classe"],
                type_inscription=self.cleaned_data["type_inscription"],
                bulletin_precedent_verifie=self.cleaned_data.get(
                    "bulletin_precedent_verifie", False
                ),
                statut=Inscription.ACTIVE,
            )

        return inscription

