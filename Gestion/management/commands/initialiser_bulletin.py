from django.core.management.base import BaseCommand
from django.db import transaction

from Gestion.models import (
    DomaineEnseignement,
    Matiere,
    ModeleBulletin,
    Niveau,
    PonderationMatiere,
    Section,
)


class Command(BaseCommand):

    help = (
        "Initialise les domaines, matieres, niveaux, "
        "Ponderations et Modeles officiels des bulletins."
    )

    # =========================================================
    # DOMAINES D'ENSEIGNEMENT
    # =========================================================

    DOMAINES = [
        {
            "code": "MATH",
            "libelle": "Mathematiques",
            "ordre": 1,
        },
        {
            "code": "SCI",
            "libelle": "Sciences",
            "ordre": 2,
        },
        {
            "code": "LANG",
            "libelle": "Langues",
            "ordre": 3,
        },
        {
            "code": "SH",
            "libelle": "Sciences humaines",
            "ordre": 4,
        },
        {
            "code": "ART",
            "libelle": "Arts",
            "ordre": 5,
        },
        {
            "code": "PD",
            "libelle": "Developpement personnel",
            "ordre": 6,
        },
        {
            "code": "EG",
            "libelle": "Electricite generale",
            "ordre": 7,
        },
    ]

    # =========================================================
    # MATIeRES DU TRONC COMMUN
    # N1 = 7eme
    # N2 = 8eme
    # =========================================================

    MATIERES_TRONC_COMMUN = [

        # -------------------------
        # MATHEMATIQUES
        # -------------------------

        {
            "code": "ALG",
            "libelle": "Algebre",
            "domaine": "MATH",
            "tj": 40,
            "examen": 80,
        },
        {
            "code": "ARI",
            "libelle": "Arithmetique",
            "domaine": "MATH",
            "tj": 10,
            "examen": 20,
        },
        {
            "code": "GEO",
            "libelle": "Geometrie",
            "domaine": "MATH",
            "tj": 20,
            "examen": 40,
        },
        {
            "code": "STA",
            "libelle": "Statistique",
            "domaine": "MATH",
            "tj": 10,
            "examen": 20,
        },

        # -------------------------
        # SCIENCES
        # -------------------------

        {
            "code": "ANA",
            "libelle": "Anatomie",
            "domaine": "SCI",
            "tj": 10,
            "examen": 20,
        },
        {
            "code": "BOT",
            "libelle": "Botanique",
            "domaine": "SCI",
            "tj": 10,
            "examen": 20,
        },
        {
            "code": "ZOO",
            "libelle": "Zoologie",
            "domaine": "SCI",
            "tj": 10,
            "examen": 20,
        },
        {
            "code": "SPH",
            "libelle": "Sciences physiques",
            "domaine": "SCI",
            "tj": 10,
            "examen": 20,
        },
        {
            "code": "TEC",
            "libelle": "Technologie",
            "domaine": "SCI",
            "tj": 10,
            "examen": 20,
        },
        {
            "code": "TIC",
            "libelle": "TIC",
            "domaine": "SCI",
            "tj": 10,
            "examen": 20,
        },

        # -------------------------
        # LANGUES
        # -------------------------

        {
            "code": "ANG",
            "libelle": "Anglais",
            "domaine": "LANG",
            "tj": 30,
            "examen": 60,
        },
        {
            "code": "FRA",
            "libelle": "Francais",
            "domaine": "LANG",
            "tj": 70,
            "examen": 140,
        },

        # -------------------------
        # SCIENCES HUMAINES
        # -------------------------

        {
            "code": "EV",
            "libelle": "education à la vie",
            "domaine": "SH",
            "tj": 20,
            "examen": 40,
        },
        {
            "code": "ECM",
            "libelle": "education civique et morale",
            "domaine": "SH",
            "tj": 20,
            "examen": 40,
        },
        {
            "code": "GEOH",
            "libelle": "Geographie",
            "domaine": "SH",
            "tj": 20,
            "examen": 40,
        },
        {
            "code": "HIS",
            "libelle": "Histoire",
            "domaine": "SH",
            "tj": 20,
            "examen": 40,
        },

        # -------------------------
        # ARTS
        # -------------------------

        {
            "code": "DES",
            "libelle": "Dessin",
            "domaine": "ART",
            "tj": 20,
            "examen": 40,
        },
        {
            "code": "MUS",
            "libelle": "Musique",
            "domaine": "ART",
            "tj": 20,
            "examen": 40,
        },

        # -------------------------
        # DEVELOPPEMENT PERSONNEL
        # -------------------------

        {
            "code": "EPS",
            "libelle": "education physique",
            "domaine": "PD",
            "tj": 20,
            "examen": 40,
        },
    ]

    # =========================================================
    # MATIeRES Electricite generale
    #
    # N3 = 1ere annee
    # N4 = 2eme annee
    # N5 = 3eme annee
    # N6 = 4eme annee
    # =========================================================

    MATIERES_ELECTRICITE = {

        # -----------------------------------------------------
        # N3 - 1ere annee
        # -----------------------------------------------------

        "N3": [
            ("EG_RELIGION", "Religion"),
            ("EG_EDUCATION_VIE", "education à la Vie"),
            ("EG_EDUCATION_CIVIQUE_MORALE",
             "education civique et morale"),
            ("EG_BIOLOGIE", "Biologie"),

            ("EG_ANGLAIS", "Anglais"),
            ("EG_CHIMIE", "Chimie"),
            ("EG_ELECTRONIQUE_NUMERIQUE",
             "electronique numerique"),
            ("EG_GEOGRAPHIE_ACTUALITES",
             "Geographie / Actualites"),
            ("EG_HISTOIRE", "Histoire"),
            ("EG_INFORMATIQUE", "Informatique"),
            ("EG_INSTRUCTION_METHODOLOGIQUE_MESURES",
             "Instruction methodologique des mesures"),
            ("EG_MECANISME", "Mecanisme"),
            ("EG_PHYSIQUE", "Physique"),
            ("EG_TECHNOLOGIE_MECANIQUE",
             "Technologie mecanique"),

            ("EG_DESSIN_ELECTRIQUE", "Dessin electrique"),
            ("EG_DESSIN_INDUSTRIEL", "Dessin industriel"),
            ("EG_ELECTRICITE_GENERALE",
             "Electricite generale"),
            ("EG_MECANIQUE_GENERALE",
             "Mecanique generale"),
            ("EG_TECHNOLOGIE_ELECTRIQUE",
             "Technologie electrique"),
            ("EG_ELECTRONIQUE", "electronique"),

            ("EG_FRANCAIS", "Francais"),
            ("EG_MATHEMATIQUES", "Mathematiques"),

            ("EG_ATELIER_ELECTRIQUE",
             "Atelier electrique"),
            ("EG_ATELIER_AJUSTAGE",
             "Atelier ajustage"),
        ],

        # -----------------------------------------------------
        # N4 - 2eme annee
        # Meme modele que N3
        # -----------------------------------------------------

        "N4": [
            ("EG_RELIGION", "Religion"),
            ("EG_EDUCATION_VIE", "education à la Vie"),
            ("EG_EDUCATION_CIVIQUE_MORALE",
             "education civique et morale"),
            ("EG_BIOLOGIE", "Biologie"),

            ("EG_ANGLAIS", "Anglais"),
            ("EG_CHIMIE", "Chimie"),
            ("EG_ELECTRONIQUE_NUMERIQUE",
             "electronique numerique"),
            ("EG_GEOGRAPHIE_ACTUALITES",
             "Geographie / Actualites"),
            ("EG_HISTOIRE", "Histoire"),
            ("EG_INFORMATIQUE", "Informatique"),
            ("EG_INSTRUCTION_METHODOLOGIQUE_MESURES",
             "Instruction methodologique des mesures"),
            ("EG_MECANISME", "Mecanisme"),
            ("EG_PHYSIQUE", "Physique"),
            ("EG_TECHNOLOGIE_MECANIQUE",
             "Technologie mecanique"),

            ("EG_DESSIN_ELECTRIQUE", "Dessin electrique"),
            ("EG_DESSIN_INDUSTRIEL", "Dessin industriel"),
            ("EG_ELECTRICITE_GENERALE",
             "Electricite generale"),
            ("EG_MECANIQUE_GENERALE",
             "Mecanique generale"),
            ("EG_TECHNOLOGIE_ELECTRIQUE",
             "Technologie electrique"),
            ("EG_ELECTRONIQUE", "electronique"),

            ("EG_FRANCAIS", "Francais"),
            ("EG_MATHEMATIQUES", "Mathematiques"),

            ("EG_ATELIER_ELECTRIQUE",
             "Atelier electrique"),
            ("EG_ATELIER_AJUSTAGE",
             "Atelier ajustage"),
        ],

        # -----------------------------------------------------
        # N5 - 3eme annee
        # -----------------------------------------------------

        "N5": [
            ("EG_RELIGION", "Religion"),
            ("EG_EDUCATION_VIE", "education à la Vie"),
            ("EG_EDUCATION_CIVIQUE_MORALE",
             "education civique et morale"),
            ("EG_BIOLOGIE", "Biologie"),

            ("EG_ACTUALITES", "Actualites"),
            ("EG_ANGLAIS", "Anglais"),
            ("EG_AUTOMATE_PROGRAMMATION",
             "Automate programmation"),
            ("EG_ELECTRONIQUE_LABO",
             "electronique + labo."),
            ("EG_INFORMATIQUE", "Informatique"),
            ("EG_INSTRUCTION_METHODOLOGIQUE_MESURES",
             "Instruction methodologique des mesures"),
            ("EG_RESISTANCES_MATERIAUX",
             "Resistances des materiaux"),

            ("EG_DESSIN_ELECTRIQUE", "Dessin electrique"),
            ("EG_ELECTRICITE_GENERALE",
             "Electricite generale"),
            ("EG_MACHINES_ELECTRIQUES",
             "Machines electriques"),
            ("EG_TECHNOLOGIE_ELECTRIQUE",
             "Technologie electrique"),

            ("EG_FRANCAIS", "Francais"),
            ("EG_MATHEMATIQUES", "Mathematiques"),

            ("EG_ATELIER_ELECTRIQUE",
             "Atelier electrique"),
            ("EG_LABORATOIRE_ELECTRIQUE",
             "Labo. electrique"),
        ],

        # -----------------------------------------------------
        # N6 - 4eme annee
        # -----------------------------------------------------

        "N6": [
            ("EG_RELIGION", "Religion"),
            ("EG_EDUCATION_VIE", "education à la Vie"),
            ("EG_EDUCATION_CIVIQUE_MORALE",
             "education civique et morale"),

            ("EG_ACTUALITES", "Actualites"),
            ("EG_ANGLAIS", "Anglais"),
            ("EG_APPLICATION_ELECTRIQUE",
             "Application electrique"),
            ("EG_AUTOMATION", "Automation"),
            ("EG_CIRCUIT_LOGIQUE",
             "Circuit logique"),
            ("EG_INFORMATIQUE", "Informatique"),
            ("EG_LEGISLATION", "Legislation"),
            ("EG_ORGANISATION", "Organisation"),

            ("EG_ELECTRONIQUE_LABO",
             "electronique + labo."),
            ("EG_MACHINE_ELECTRIQUE",
             "Machine electrique"),
            ("EG_MECANIQUE_APPLIQUEE",
             "Mecanique appliquee"),
            ("EG_SCHEMA", "Schema"),

            ("EG_DESSIN_ELECTRIQUE",
             "Dessin electrique"),
            ("EG_FRANCAIS", "Francais"),
            ("EG_LABORATOIRE_ELECTRIQUE",
             "Labo. electrique"),
            ("EG_MATHEMATIQUES", "Mathematiques"),

            ("EG_ATELIER_ELECTRIQUE",
             "Atelier electrique"),
        ],
    }

    # =========================================================
    # NIVEAUX
    # =========================================================

    NIVEAUX = [
        {
            "code": "N1",
            "libelle": "NIVEAU 1",
            "ordre": 1,
            "est_ecole_base": True,
        },
        {
            "code": "N2",
            "libelle": "NIVEAU 2",
            "ordre": 2,
            "est_ecole_base": True,
        },
        {
            "code": "N3",
            "libelle": "NIVEAU 3",
            "ordre": 3,
            "est_ecole_base": False,
        },
        {
            "code": "N4",
            "libelle": "NIVEAU 4",
            "ordre": 4,
            "est_ecole_base": False,
        },
        {
            "code": "N5",
            "libelle": "NIVEAU 5",
            "ordre": 5,
            "est_ecole_base": False,
        },
        {
            "code": "N6",
            "libelle": "NIVEAU 6",
            "ordre": 6,
            "est_ecole_base": False,
        },
    ]

    SECTIONS = [
        {
            "code": "ELEC",
            "libelle": "ELECTRICITE",
        },
        {
            "code": "PEDA",
            "libelle": "PEDAGOGIE",
        },
    ]

    EG_TJ_DEFAULT = 20
    EG_EXAMEN_DEFAULT = 40

    # =========================================================
    # Modeles DE BULLETIN
    # =========================================================

    MODELES_BULLETIN = [
        {
            "code": "BUL-TC-7",
            "libelle": "Bulletin officiel - Tronc commun - 7eme annee",
            "niveau_code": "N1",
        },
        {
            "code": "BUL-TC-8",
            "libelle": "Bulletin officiel - Tronc commun - 8eme annee",
            "niveau_code": "N2",
        },
        {
            "code": "BUL-EG-1",
            "libelle": "Bulletin officiel - Electricite generale - 1ere annee",
            "niveau_code": "N3",
        },
        {
            "code": "BUL-EG-2",
            "libelle": "Bulletin officiel - Electricite generale - 2eme annee",
            "niveau_code": "N4",
        },
        {
            "code": "BUL-EG-3",
            "libelle": "Bulletin officiel - Electricite generale - 3eme annee",
            "niveau_code": "N5",
        },
        {
            "code": "BUL-EG-4",
            "libelle": "Bulletin officiel - Electricite generale - 4eme annee",
            "niveau_code": "N6",
        },
    ]

    # =========================================================
    # HANDLE
    # =========================================================

    def _creer_ponderation(
        self,
        niveau,
        section,
        matiere,
        travaux_journaliers_max,
        examen_max,
    ):
        total_semestre = (
            travaux_journaliers_max * 2
        ) + examen_max

        ponderation, created = (
            PonderationMatiere.objects.update_or_create(
                niveau=niveau,
                section=section,
                matiere=matiere,
                defaults={
                    "travaux_journaliers_max": travaux_journaliers_max,
                    "examen_max": examen_max,
                    "actif": True,
                },
            )
        )

        return ponderation, created, total_semestre

    @transaction.atomic
    def handle(self, *args, **options):

        self.stdout.write(
            self.style.NOTICE(
                "\n=== INITIALISATION DU BULLETIN ===\n"
            )
        )

        # =====================================================
        # 1. DOMAINES
        # =====================================================

        domaines = {}

        for data in self.DOMAINES:

            domaine, created = (
                DomaineEnseignement.objects.update_or_create(
                    code=data["code"],
                    defaults={
                        "libelle": data["libelle"],
                        "ordre": data["ordre"],
                        "actif": True,
                    },
                )
            )

            domaines[data["code"]] = domaine

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Domaine cree : {domaine.libelle}"
                    )
                )
            else:
                self.stdout.write(
                    f"Domaine existant : {domaine.libelle}"
                )

        # =====================================================
        # 2. MATIeRES DU TRONC COMMUN
        # =====================================================

        matieres = {}

        for data in self.MATIERES_TRONC_COMMUN:

            domaine = domaines[data["domaine"]]

            matiere, created = (
                Matiere.objects.update_or_create(
                    code=data["code"],
                    defaults={
                        "domaine": domaine,
                        "libelle": data["libelle"],
                        "actif": True,
                    },
                )
            )

            matieres[data["code"]] = matiere

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Matiere creee : {matiere.libelle}"
                    )
                )
            else:
                self.stdout.write(
                    f"Matiere existante : {matiere.libelle}"
                )

        # =====================================================
        # 3. MATIeRES Electricite generale
        # =====================================================

        matieres_electricite = {}

        for niveau_code, liste_matieres in (
            self.MATIERES_ELECTRICITE.items()
        ):

            self.stdout.write(
                self.style.NOTICE(
                    f"\nMatieres Electricite - {niveau_code}"
                )
            )

            for code, libelle in liste_matieres:

                matiere, created = (
                    Matiere.objects.update_or_create(
                        code=code,
                        defaults={
                            "domaine": domaines["EG"],
                            "libelle": libelle,
                            "actif": True,
                        },
                    )
                )

                matieres_electricite[code] = matiere

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Matiere creee : {matiere.libelle}"
                        )
                    )
                else:
                    self.stdout.write(
                        f"Matiere existante : {matiere.libelle}"
                    )

        # =====================================================
        # 4. ReCUPeRATION / mise a jour DES NIVEAUX
        # =====================================================

        niveaux = {}

        for data in self.NIVEAUX:

            try:
                niveau = Niveau.objects.get(
                    code=data["code"]
                )

            except Niveau.DoesNotExist:

                try:
                    niveau = Niveau.objects.get(
                        libelle=data["libelle"]
                    )

                except Niveau.DoesNotExist:

                    self.stdout.write(
                        self.style.ERROR(
                            f"Niveau introuvable : "
                            f"{data['code']} / "
                            f"{data['libelle']}"
                        )
                    )
                    raise

            # On met à jour les informations du niveau existant.
            niveau.ordre = data["ordre"]
            niveau.est_ecole_base = data["est_ecole_base"]
            niveau.actif = True
            niveau.save(
                update_fields=[
                    "ordre",
                    "est_ecole_base",
                    "actif",
                ]
            )

            niveaux[data["code"]] = niveau

            self.stdout.write(
                self.style.SUCCESS(
                    f"Niveau utilise : "
                    f"{niveau.code} - {niveau.libelle}"
                )
            )

        sections = {}

        for data in self.SECTIONS:
            section, created = (
                Section.objects.update_or_create(
                    code=data["code"],
                    defaults={
                        "libelle": data["libelle"],
                        "actif": True,
                    },
                )
            )
            sections[data["code"]] = section

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Section creee : {section.libelle}"
                    )
                )
            else:
                self.stdout.write(
                    f"Section existante : {section.libelle}"
                )

        # =====================================================
        # 5. Ponderations DU TRONC COMMUN
        #
        # IMPORTANT :
        # Les matieres EG ne sont PAS ajoutees ici.
        # =====================================================

        total_ponderations = 0

        for niveau_code in ["N1", "N2"]:

            niveau = niveaux[niveau_code]

            self.stdout.write(
                self.style.NOTICE(
                    f"\nPonderations pour {niveau.libelle}"
                )
            )

            for data in self.MATIERES_TRONC_COMMUN:

                matiere = matieres[data["code"]]
                ponderation, created, total_semestre = (
                    self._creer_ponderation(
                        niveau,
                        None,
                        matiere,
                        data["tj"],
                        data["examen"],
                    )
                )

                total_ponderations += 1

                action = (
                    "creee"
                    if created
                    else "mise a jour"
                )

                self.stdout.write(
                    f"  {matiere.libelle} : "
                    f"TJ={data['tj']}, "
                    f"Examen={data['examen']}, "
                    f"Total semestre={total_semestre} "
                    f"-> {action}"
                )

        for niveau_code in ["N3", "N4", "N5", "N6"]:

            niveau = niveaux[niveau_code]

            for section in sections.values():

                self.stdout.write(
                    self.style.NOTICE(
                        f"\nPonderations pour {niveau.libelle} "
                        f"- {section.libelle}"
                    )
                )

                for data in self.MATIERES_TRONC_COMMUN:

                    matiere = matieres[data["code"]]
                    ponderation, created, total_semestre = (
                        self._creer_ponderation(
                            niveau,
                            section,
                            matiere,
                            data["tj"],
                            data["examen"],
                        )
                    )

                    total_ponderations += 1

                    action = (
                        "creee"
                        if created
                        else "mise a jour"
                    )

                    self.stdout.write(
                        f"  [{section.code}] {matiere.libelle} : "
                        f"TJ={data['tj']}, "
                        f"Examen={data['examen']}, "
                        f"Total semestre={total_semestre} "
                        f"-> {action}"
                    )

                for code, _libelle in (
                    self.MATIERES_ELECTRICITE[niveau_code]
                ):

                    matiere = matieres_electricite[code]
                    ponderation, created, total_semestre = (
                        self._creer_ponderation(
                            niveau,
                            section,
                            matiere,
                            self.EG_TJ_DEFAULT,
                            self.EG_EXAMEN_DEFAULT,
                        )
                    )

                    total_ponderations += 1

                    action = (
                        "creee"
                        if created
                        else "mise a jour"
                    )

                    self.stdout.write(
                        f"  [{section.code}] {matiere.libelle} : "
                        f"TJ={self.EG_TJ_DEFAULT}, "
                        f"Examen={self.EG_EXAMEN_DEFAULT}, "
                        f"Total semestre={total_semestre} "
                        f"-> {action}"
                    )

        # =====================================================
        # 6. Modeles DE BULLETIN
        # =====================================================

        total_modeles = 0

        self.stdout.write(
            self.style.NOTICE(
                "\nCreation des Modeles de bulletin"
            )
        )

        for data in self.MODELES_BULLETIN:

            niveau = niveaux[data["niveau_code"]]

            modele, created = (
                ModeleBulletin.objects.update_or_create(
                    code=data["code"],
                    defaults={
                        "libelle": data["libelle"],
                        "niveau": niveau,
                        "section": None,
                        "version": 1,
                        "actif": True,
                    },
                )
            )

            total_modeles += 1

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"-> Modele cree : {modele.code}"
                    )
                )
            else:
                self.stdout.write(
                    f"-> Modele existant : {modele.code}"
                )

        # =====================================================
        # 7. VeRIFICATION DES TOTAUX DU TRONC COMMUN
        # =====================================================

        total_tj = sum(
            data["tj"]
            for data in self.MATIERES_TRONC_COMMUN
        )

        total_examen = sum(
            data["examen"]
            for data in self.MATIERES_TRONC_COMMUN
        )

        total_semestre = (
            total_tj * 2
        ) + total_examen

        total_annuel = total_semestre * 2

        # =====================================================
        # 8. RAPPORT FINAL
        # =====================================================

        self.stdout.write("\n")

        self.stdout.write(
            self.style.SUCCESS(
                "=============================================="
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                " INITIALISATION DU BULLETIN TERMINeE"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "=============================================="
            )
        )

        self.stdout.write(
            f"Domaines traites : {len(self.DOMAINES)}"
        )

        self.stdout.write(
            f"Matieres tronc commun : "
            f"{len(self.MATIERES_TRONC_COMMUN)}"
        )

        total_matieres_eg = sum(
            len(liste)
            for liste in self.MATIERES_ELECTRICITE.values()
        )

        self.stdout.write(
            f"Entrees matieres Electricite : "
            f"{total_matieres_eg}"
        )

        self.stdout.write(
            f"Niveaux traites : {len(self.NIVEAUX)}"
        )

        self.stdout.write(
            f"Sections specialisees : {len(sections)}"
        )

        self.stdout.write(
            f"Ponderations traitees : "
            f"{total_ponderations}"
        )

        self.stdout.write(
            f"Modeles de bulletin : {total_modeles}"
        )

        self.stdout.write(
            f"\nMaximum TJ / semestre : {total_tj}"
        )

        self.stdout.write(
            f"Maximum examen / semestre : "
            f"{total_examen}"
        )

        self.stdout.write(
            f"Maximum total / semestre : "
            f"{total_semestre}"
        )

        self.stdout.write(
            f"Maximum annuel : {total_annuel}"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\nLes Donnees existantes ont Ete conservees."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "La commande peut etre executee à nouveau "
                "sans creer de doublons."
            )
        )