from django.core.management.base import BaseCommand

from Gestion.models import (
    Role,
    Permission,
    RolePermission,
    TypeAction,
)


class Command(BaseCommand):

    help = (
        "Initialise les rôles, permissions, associations "
        "et types d'actions du système."
    )

    # ============================================================
    # RÔLES
    # ============================================================

    ROLES = {

        "ADMIN": "Administrateur",

        "PROMOTEUR": "Promoteur",

        "DIRECTEUR": "Directeur",

        "PREFET": "Préfet des études",

        "SECRETAIRE": "Secrétaire / Scolarité",

        "ENSEIGNANT": "Enseignant",

        "DIRECTEUR_DISCIPLINE": (
            "Directeur de discipline"
        ),

        "COMPTABLE": "Comptable",
    }

    # ============================================================
    # PERMISSIONS
    # ============================================================

    PERMISSIONS = {

        # --------------------------------------------------------
        # UTILISATEURS
        # --------------------------------------------------------

        "utilisateur.consulter":
            "Consulter les utilisateurs",

        "utilisateur.creer":
            "Créer un utilisateur",

        "utilisateur.modifier":
            "Modifier un utilisateur",

        "utilisateur.desactiver":
            "Désactiver un utilisateur",

        "utilisateur.activer":
            "Activer un utilisateur",

        "utilisateur.reinitialiser_mdp":
            "Réinitialiser un mot de passe",


        # --------------------------------------------------------
        # RÔLES ET PERMISSIONS
        # --------------------------------------------------------

        "role.consulter":
            "Consulter les rôles",

        "role.creer":
            "Créer un rôle",

        "role.modifier":
            "Modifier un rôle",

        "role.desactiver":
            "Désactiver un rôle",

        "permission.consulter":
            "Consulter les permissions",

        "permission.attribuer":
            "Attribuer une permission à un rôle",

        "permission.retirer":
            "Retirer une permission d'un rôle",


        # --------------------------------------------------------
        # ANNÉE SCOLAIRE
        # --------------------------------------------------------

        "annee.consulter":
            "Consulter les années scolaires",

        "annee.creer":
            "Créer une année scolaire",

        "annee.modifier":
            "Modifier une année scolaire",

        "annee.activer":
            "Activer une année scolaire",

        "annee.cloturer":
            "Clôturer une année scolaire",


        # --------------------------------------------------------
        # STRUCTURE ACADÉMIQUE
        # --------------------------------------------------------

        "section.consulter":
            "Consulter les sections",

        "section.creer":
            "Créer une section",

        "section.modifier":
            "Modifier une section",

        "section.desactiver":
            "Désactiver une section",


        "niveau.consulter":
            "Consulter les niveaux",

        "niveau.creer":
            "Créer un niveau",

        "niveau.modifier":
            "Modifier un niveau",

        "niveau.desactiver":
            "Désactiver un niveau",


        "classe.consulter":
            "Consulter les classes",

        "classe.creer":
            "Créer une classe",

        "classe.modifier":
            "Modifier une classe",

        "classe.desactiver":
            "Désactiver une classe",


        "matiere.consulter":
            "Consulter les matières",

        "matiere.creer":
            "Créer une matière",

        "matiere.modifier":
            "Modifier une matière",

        "matiere.desactiver":
            "Désactiver une matière",


        # --------------------------------------------------------
        # ÉLÈVES
        # --------------------------------------------------------

        "eleve.consulter":
            "Consulter les élèves",

        "eleve.creer":
            "Créer un élève",

        "eleve.modifier":
            "Modifier un élève",

        "eleve.desactiver":
            "Désactiver un élève",


        # --------------------------------------------------------
        # RESPONSABLES LÉGAUX
        # --------------------------------------------------------

        "responsable.consulter":
            "Consulter les responsables légaux",

        "responsable.creer":
            "Créer un responsable légal",

        "responsable.modifier":
            "Modifier un responsable légal",

        "responsable.desactiver":
            "Désactiver un responsable légal",


        # --------------------------------------------------------
        # INSCRIPTIONS
        # --------------------------------------------------------

        "inscription.consulter":
            "Consulter les inscriptions",

        "inscription.creer":
            "Créer une inscription",

        "inscription.modifier":
            "Modifier une inscription",

        "inscription.annuler":
            "Annuler une inscription",

        "inscription.reinscrire":
            "Effectuer une réinscription",

        "inscription.verifier_bulletin":
            "Vérifier le bulletin précédent",


        # --------------------------------------------------------
        # ENSEIGNANTS
        # --------------------------------------------------------

        "enseignant.consulter":
            "Consulter les enseignants",

        "enseignant.creer":
            "Créer un enseignant",

        "enseignant.modifier":
            "Modifier un enseignant",

        "enseignant.desactiver":
            "Désactiver un enseignant",


        # --------------------------------------------------------
        # AFFECTATIONS
        # --------------------------------------------------------

        "affectation.consulter":
            "Consulter les affectations",

        "affectation.creer":
            "Créer une affectation",

        "affectation.modifier":
            "Modifier une affectation",

        "affectation.desactiver":
            "Désactiver une affectation",


        # --------------------------------------------------------
        # TITULARISATION
        # --------------------------------------------------------

        "titularisation.consulter":
            "Consulter les titularisations",

        "titularisation.attribuer":
            "Attribuer un titulaire",

        "titularisation.modifier":
            "Modifier une titularisation",

        "titularisation.annuler":
            "Annuler une titularisation",


        # --------------------------------------------------------
        # SEMESTRES
        # --------------------------------------------------------

        "semestre.consulter":
            "Consulter les semestres",

        "semestre.ouvrir":
            "Ouvrir un semestre",

        "semestre.cloturer":
            "Clôturer un semestre",

        "semestre.verrouiller":
            "Verrouiller un semestre",


        # --------------------------------------------------------
        # PÉRIODES
        # --------------------------------------------------------

        "periode.consulter":
            "Consulter les périodes",

        "periode.ouvrir":
            "Ouvrir une période",

        "periode.cloturer":
            "Clôturer une période",

        "periode.verrouiller":
            "Verrouiller une période",


        # --------------------------------------------------------
        # PONDÉRATIONS
        # --------------------------------------------------------

        "ponderation.consulter":
            "Consulter les pondérations",

        "ponderation.creer":
            "Créer une pondération",

        "ponderation.modifier":
            "Modifier une pondération",

        "ponderation.desactiver":
            "Désactiver une pondération",


        # --------------------------------------------------------
        # ÉVALUATIONS
        # --------------------------------------------------------

        "evaluation.consulter":
            "Consulter les évaluations",

        "evaluation.creer":
            "Créer une évaluation",

        "evaluation.modifier":
            "Modifier une évaluation",

        "evaluation.cloturer":
            "Clôturer une évaluation",

        "evaluation.verrouiller":
            "Verrouiller une évaluation",


        # --------------------------------------------------------
        # RÉSULTATS DES ÉVALUATIONS
        # --------------------------------------------------------

        "resultat.consulter":
            "Consulter les résultats",

        "resultat.saisir":
            "Saisir un résultat",

        "resultat.modifier":
            "Modifier un résultat",

        "resultat.verrouiller":
            "Verrouiller un résultat",


        # --------------------------------------------------------
        # EXAMENS
        # --------------------------------------------------------

        "examen.consulter":
            "Consulter les examens",

        "examen.creer":
            "Créer un examen",

        "examen.modifier":
            "Modifier un examen",

        "examen.cloturer":
            "Clôturer un examen",

        "examen.verrouiller":
            "Verrouiller un examen",


        # --------------------------------------------------------
        # RÉSULTATS DES EXAMENS
        # --------------------------------------------------------

        "resultat_examen.consulter":
            "Consulter les résultats des examens",

        "resultat_examen.saisir":
            "Saisir un résultat d'examen",

        "resultat_examen.modifier":
            "Modifier un résultat d'examen",

        "resultat_examen.verrouiller":
            "Verrouiller un résultat d'examen",


        # --------------------------------------------------------
        # RÉSULTATS DE PÉRIODE
        # --------------------------------------------------------

        "resultat_periode.consulter":
            "Consulter les résultats de période",

        "resultat_periode.calculer":
            "Calculer les résultats de période",

        "resultat_periode.verrouiller":
            "Verrouiller les résultats de période",


        # --------------------------------------------------------
        # RÉSULTATS DE SEMESTRE
        # --------------------------------------------------------

        "resultat_semestre.consulter":
            "Consulter les résultats de semestre",

        "resultat_semestre.calculer":
            "Calculer les résultats de semestre",

        "resultat_semestre.verrouiller":
            "Verrouiller les résultats de semestre",


        # --------------------------------------------------------
        # RÉSULTATS ANNUELS
        # --------------------------------------------------------

        "resultat_annuel.consulter":
            "Consulter les résultats annuels",

        "resultat_annuel.calculer":
            "Calculer les résultats annuels",

        "resultat_annuel.verrouiller":
            "Verrouiller les résultats annuels",

        "resultat_annuel.decider":
            "Prendre une décision annuelle",


        # --------------------------------------------------------
        # MODÈLES DE BULLETIN
        # --------------------------------------------------------

        "modele_bulletin.consulter":
            "Consulter les modèles de bulletin",

        "modele_bulletin.creer":
            "Créer un modèle de bulletin",

        "modele_bulletin.modifier":
            "Modifier un modèle de bulletin",

        "modele_bulletin.desactiver":
            "Désactiver un modèle de bulletin",


        # --------------------------------------------------------
        # BULLETINS
        # --------------------------------------------------------

        "bulletin.consulter":
            "Consulter les bulletins",

        "bulletin.generer":
            "Générer un bulletin",

        "bulletin.valider":
            "Valider un bulletin",

        "bulletin.verrouiller":
            "Verrouiller un bulletin",

        "bulletin.annuler":
            "Annuler un bulletin",

        "bulletin.signer":
            "Signer un bulletin",


        # --------------------------------------------------------
        # PROCLAMATIONS
        # --------------------------------------------------------

        "proclamation.consulter":
            "Consulter les proclamations",

        "proclamation.creer":
            "Créer une proclamation",

        "proclamation.valider":
            "Valider une proclamation",

        "proclamation.annuler":
            "Annuler une proclamation",


        # --------------------------------------------------------
        # HORAIRES
        # --------------------------------------------------------

        "horaire.consulter":
            "Consulter les horaires",

        "horaire.creer":
            "Créer un horaire",

        "horaire.modifier":
            "Modifier un horaire",

        "horaire.desactiver":
            "Désactiver un horaire",


        # --------------------------------------------------------
        # PRÉSENCES
        # --------------------------------------------------------

        "presence.consulter":
            "Consulter les présences",

        "presence.saisir":
            "Saisir les présences",

        "presence.modifier":
            "Modifier une présence",

        "presence.justifier":
            "Justifier une absence",


        # --------------------------------------------------------
        # ABANDONS
        # --------------------------------------------------------

        "abandon.consulter":
            "Consulter les abandons",

        "abandon.declarer":
            "Déclarer un abandon",

        "abandon.valider":
            "Valider un abandon",

        "abandon.annuler":
            "Annuler un abandon",


        # --------------------------------------------------------
        # FINANCES
        # --------------------------------------------------------

        "finance.consulter":
            "Consulter les informations financières",


        "calendrier_financier.consulter":
            "Consulter le calendrier financier",

        "calendrier_financier.creer":
            "Créer un calendrier financier",

        "calendrier_financier.modifier":
            "Modifier un calendrier financier",

        "calendrier_financier.cloturer":
            "Clôturer le calendrier financier",


        "frais.consulter":
            "Consulter les frais scolaires",

        "frais.creer":
            "Créer les frais scolaires",

        "frais.modifier":
            "Modifier les frais scolaires",

        "frais.desactiver":
            "Désactiver les frais scolaires",


        "tranche.consulter":
            "Consulter les tranches",

        "tranche.creer":
            "Créer une tranche",

        "tranche.modifier":
            "Modifier une tranche",


        # --------------------------------------------------------
        # PAIEMENTS
        # --------------------------------------------------------

        "paiement.consulter":
            "Consulter les paiements",

        "paiement.enregistrer":
            "Enregistrer un paiement",

        "paiement.valider":
            "Valider un paiement",

        "paiement.annuler":
            "Annuler un paiement",


        # --------------------------------------------------------
        # REÇUS
        # --------------------------------------------------------

        "recu.consulter":
            "Consulter les reçus",

        "recu.generer":
            "Générer un reçu",

        "recu.valider":
            "Valider un reçu",

        "recu.annuler":
            "Annuler un reçu",


        # --------------------------------------------------------
        # CAISSE
        # --------------------------------------------------------

        "caisse.consulter":
            "Consulter la caisse",

        "caisse.ouvrir":
            "Ouvrir la caisse",

        "caisse.fermer":
            "Fermer la caisse",

        "caisse.enregistrer_entree":
            "Enregistrer une entrée de caisse",

        "caisse.enregistrer_sortie":
            "Enregistrer une sortie de caisse",

        "caisse.valider_sortie":
            "Valider une sortie de caisse",


        # --------------------------------------------------------
        # AUTORISATIONS
        # --------------------------------------------------------

        "autorisation.consulter":
            "Consulter les demandes d'autorisation",

        "autorisation.demander":
            "Demander une autorisation",

        "autorisation.approuver":
            "Approuver une autorisation",

        "autorisation.refuser":
            "Refuser une autorisation",

        "autorisation.annuler":
            "Annuler une demande d'autorisation",


        # --------------------------------------------------------
        # AUDIT / HISTORIQUE
        # --------------------------------------------------------

        "audit.consulter":
            "Consulter les historiques",

        "audit.rechercher":
            "Rechercher dans les historiques",

        "audit.consulter_anomalies":
            "Consulter les anomalies",

        "audit.traiter_anomalie":
            "Traiter une anomalie",


        # --------------------------------------------------------
        # NOTIFICATIONS
        # --------------------------------------------------------

        "notification.consulter":
            "Consulter les notifications",

        "notification.creer":
            "Créer une notification",

        "notification.envoyer":
            "Envoyer une notification",

        "notification.lire":
            "Lire une notification",


        # --------------------------------------------------------
        # TABLEAUX DE BORD / RAPPORTS
        # --------------------------------------------------------

        "dashboard.consulter":
            "Consulter le tableau de bord",

        "rapport.consulter":
            "Consulter les rapports",

        "rapport.generer":
            "Générer les rapports",
    }


    # ============================================================
    # PERMISSIONS PAR RÔLE
    # ============================================================

    ROLE_PERMISSIONS = {

        # ========================================================
        # ADMINISTRATEUR
        # ========================================================

        "ADMIN": list(PERMISSIONS.keys()),


        # ========================================================
        # PROMOTEUR
        # ========================================================

        "PROMOTEUR": [

            "utilisateur.consulter",

            "annee.consulter",
            "section.consulter",
            "niveau.consulter",
            "classe.consulter",
            "matiere.consulter",

            "eleve.consulter",
            "responsable.consulter",
            "inscription.consulter",

            "enseignant.consulter",
            "affectation.consulter",
            "titularisation.consulter",

            "semestre.consulter",
            "periode.consulter",
            "ponderation.consulter",
            "evaluation.consulter",
            "resultat.consulter",
            "examen.consulter",
            "resultat_examen.consulter",
            "resultat_periode.consulter",
            "resultat_semestre.consulter",
            "resultat_annuel.consulter",

            "modele_bulletin.consulter",
            "bulletin.consulter",
            "proclamation.consulter",

            "horaire.consulter",
            "presence.consulter",
            "abandon.consulter",

            "finance.consulter",
            "calendrier_financier.consulter",
            "frais.consulter",
            "tranche.consulter",
            "paiement.consulter",
            "recu.consulter",
            "caisse.consulter",

            "autorisation.consulter",
            "autorisation.approuver",
            "autorisation.refuser",

            "audit.consulter",
            "audit.rechercher",
            "audit.consulter_anomalies",

            "notification.consulter",

            "rapport.consulter",
            "rapport.generer",

            "dashboard.consulter",
        ],


        # ========================================================
        # DIRECTEUR
        # ========================================================

        "DIRECTEUR": [

            "utilisateur.consulter",

            "annee.consulter",
            "section.consulter",
            "niveau.consulter",
            "classe.consulter",
            "matiere.consulter",
            "matiere.creer",
            "matiere.modifier",

            "eleve.consulter",
            "responsable.consulter",
            "inscription.consulter",

            "enseignant.consulter",

            "affectation.consulter",
            "affectation.creer",
            "affectation.modifier",
            "affectation.desactiver",

            "titularisation.consulter",
            "titularisation.attribuer",

            "semestre.consulter",
            "periode.consulter",
            "ponderation.consulter",
            "evaluation.consulter",
            "resultat.consulter",
            "examen.consulter",
            "resultat_examen.consulter",

            "resultat_periode.consulter",
            "resultat_semestre.consulter",
            "resultat_annuel.consulter",

            "bulletin.consulter",
            "bulletin.valider",
            "bulletin.verrouiller",

            "proclamation.consulter",
            "proclamation.creer",
            "proclamation.valider",

            "horaire.consulter",
            "presence.consulter",

            "abandon.consulter",
            "abandon.valider",

            "finance.consulter",
            "paiement.consulter",
            "recu.consulter",
            "caisse.consulter",

            "autorisation.consulter",
            "autorisation.approuver",
            "autorisation.refuser",

            "audit.consulter",
            "audit.rechercher",
            "audit.consulter_anomalies",

            "notification.consulter",

            "rapport.consulter",
            "rapport.generer",

            "dashboard.consulter",
        ],


        # ========================================================
        # PRÉFET DES ÉTUDES
        # ========================================================

        "PREFET": [

            "annee.consulter",

            "section.consulter",
            "niveau.consulter",
            "classe.consulter",
            "matiere.consulter",

            "eleve.consulter",
            "responsable.consulter",
            "inscription.consulter",

            "enseignant.consulter",

            "affectation.consulter",
            "affectation.creer",
            "affectation.modifier",

            "titularisation.consulter",
            "titularisation.attribuer",
            "titularisation.modifier",

            "semestre.consulter",
            "periode.consulter",

            "ponderation.consulter",
            "ponderation.creer",
            "ponderation.modifier",

            "evaluation.consulter",

            "resultat.consulter",

            "examen.consulter",
            "resultat_examen.consulter",

            "resultat_periode.consulter",
            "resultat_periode.calculer",

            "resultat_semestre.consulter",
            "resultat_semestre.calculer",

            "resultat_annuel.consulter",
            "resultat_annuel.calculer",
            "resultat_annuel.decider",

            "modele_bulletin.consulter",

            "bulletin.consulter",
            "bulletin.generer",
            "bulletin.valider",
            "bulletin.verrouiller",

            "proclamation.consulter",
            "proclamation.creer",
            "proclamation.valider",

            "horaire.consulter",
            "horaire.creer",
            "horaire.modifier",

            "presence.consulter",

            "abandon.consulter",
            "abandon.valider",

            "autorisation.consulter",
            "autorisation.approuver",
            "autorisation.refuser",

            "notification.consulter",
            "notification.creer",
            "notification.envoyer",

            "audit.consulter",
            "audit.rechercher",

            "rapport.consulter",
            "rapport.generer",

            "dashboard.consulter",
        ],


        # ========================================================
        # SECRÉTAIRE / SCOLARITÉ
        # ========================================================

        "SECRETAIRE": [

            "eleve.consulter",
            "eleve.creer",
            "eleve.modifier",

            "responsable.consulter",
            "responsable.creer",
            "responsable.modifier",

            "inscription.consulter",
            "inscription.creer",
            "inscription.modifier",
            "inscription.reinscrire",
            "inscription.verifier_bulletin",

            "classe.consulter",
            "section.consulter",
            "niveau.consulter",

            "enseignant.consulter",

            "bulletin.consulter",

            "notification.consulter",

            "dashboard.consulter",
        ],


        # ========================================================
        # ENSEIGNANT
        # ========================================================

        "ENSEIGNANT": [

            "eleve.consulter",

            "inscription.consulter",

            "matiere.consulter",
            "classe.consulter",

            "affectation.consulter",

            "evaluation.consulter",
            "evaluation.creer",
            "evaluation.modifier",

            "resultat.consulter",
            "resultat.saisir",
            "resultat.modifier",

            "examen.consulter",

            "resultat_examen.consulter",
            "resultat_examen.saisir",
            "resultat_examen.modifier",

            "resultat_periode.consulter",

            "horaire.consulter",

            "presence.consulter",
            "presence.saisir",
            "presence.modifier",

            "notification.consulter",

            "dashboard.consulter",
        ],


        # ========================================================
        # DIRECTEUR DE DISCIPLINE
        # ========================================================

        "DIRECTEUR_DISCIPLINE": [

            "eleve.consulter",

            "inscription.consulter",

            "classe.consulter",

            "horaire.consulter",

            "presence.consulter",
            "presence.modifier",
            "presence.justifier",

            "abandon.consulter",
            "abandon.declarer",
            "abandon.valider",

            "notification.consulter",
            "notification.creer",
            "notification.envoyer",

            "rapport.consulter",
            "rapport.generer",

            "dashboard.consulter",
        ],


        # ========================================================
        # COMPTABLE
        # ========================================================

        "COMPTABLE": [

            "eleve.consulter",

            "inscription.consulter",

            "finance.consulter",

            "calendrier_financier.consulter",

            "frais.consulter",

            "tranche.consulter",

            "paiement.consulter",
            "paiement.enregistrer",
            "paiement.valider",

            "recu.consulter",
            "recu.generer",
            "recu.valider",

            "caisse.consulter",
            "caisse.ouvrir",
            "caisse.fermer",
            "caisse.enregistrer_entree",
            "caisse.enregistrer_sortie",
            "caisse.valider_sortie",

            "autorisation.consulter",
            "autorisation.demander",

            "notification.consulter",

            "rapport.consulter",
            "rapport.generer",

            "dashboard.consulter",
        ],
    }


    # ============================================================
    # TYPES D'ACTIONS
    # ============================================================

    TYPES_ACTIONS = [

        # --------------------------------------------------------
        # UTILISATEURS
        # --------------------------------------------------------

        {
            "code": "UTILISATEUR_CREATION",
            "libelle": "Création d'un utilisateur",
        },

        {
            "code": "UTILISATEUR_MODIFICATION",
            "libelle": "Modification d'un utilisateur",
        },

        {
            "code": "UTILISATEUR_ACTIVATION",
            "libelle": "Activation d'un utilisateur",
        },

        {
            "code": "UTILISATEUR_DESACTIVATION",
            "libelle": "Désactivation d'un utilisateur",
        },

        {
            "code": "UTILISATEUR_REINITIALISATION_MDP",
            "libelle": "Réinitialisation du mot de passe",
        },
    ]


    # ============================================================
    # EXÉCUTION
    # ============================================================

    def handle(self, *args, **options):

        self.stdout.write("")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Initialisation des rôles et permissions"
            )
        )

        self.stdout.write("")

        # --------------------------------------------------------
        # 1. CRÉATION DES PERMISSIONS
        # --------------------------------------------------------

        permissions = {}

        for code, libelle in self.PERMISSIONS.items():

            permission, created = (
                Permission.objects.get_or_create(
                    code=code,
                    defaults={
                        "libelle": libelle,
                    },
                )
            )

            if (
                not created
                and permission.libelle != libelle
            ):
                permission.libelle = libelle

                permission.save(
                    update_fields=["libelle"]
                )

            permissions[code] = permission

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {len(permissions)} permissions disponibles."
            )
        )


        # --------------------------------------------------------
        # 2. CRÉATION DES RÔLES
        # --------------------------------------------------------

        roles = {}

        for code, libelle in self.ROLES.items():

            role, created = (
                Role.objects.get_or_create(
                    code=code,
                    defaults={
                        "libelle": libelle,
                        "actif": True,
                    },
                )
            )

            if not created:

                modifications = []

                if role.libelle != libelle:

                    role.libelle = libelle

                    modifications.append("libelle")

                if not role.actif:

                    role.actif = True

                    modifications.append("actif")

                if modifications:

                    role.save(
                        update_fields=modifications
                    )

            roles[code] = role

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {len(roles)} rôles disponibles."
            )
        )


        # --------------------------------------------------------
        # 3. ASSOCIATION RÔLES → PERMISSIONS
        # --------------------------------------------------------

        total_associations = 0

        for (
            role_code,
            permission_codes
        ) in self.ROLE_PERMISSIONS.items():

            role = roles[role_code]

            for permission_code in permission_codes:

                permission = permissions.get(
                    permission_code
                )

                if permission is None:

                    self.stdout.write(
                        self.style.WARNING(
                            "⚠ Permission inconnue : "
                            f"{permission_code}"
                        )
                    )

                    continue

                _, created = (
                    RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                    )
                )

                if created:

                    total_associations += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {total_associations} "
                "nouvelles associations créées."
            )
        )


        # --------------------------------------------------------
        # 4. CRÉATION DES TYPES D'ACTIONS
        # --------------------------------------------------------

        total_types_actions = 0

        for donnees in self.TYPES_ACTIONS:

            type_action, created = (
                TypeAction.objects.get_or_create(
                    code=donnees["code"],
                    defaults={
                        "libelle": donnees["libelle"],
                    },
                )
            )

            if (
                not created
                and type_action.libelle
                != donnees["libelle"]
            ):
                type_action.libelle = (
                    donnees["libelle"]
                )

                type_action.save(
                    update_fields=["libelle"]
                )

            if created:

                total_types_actions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {total_types_actions} "
                "nouveaux types d'actions créés."
            )
        )


        # --------------------------------------------------------
        # 5. VÉRIFICATION
        # --------------------------------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Résumé des permissions par rôle"
            )
        )

        self.stdout.write("")

        for role_code, role in roles.items():

            nombre = (
                RolePermission.objects
                .filter(role=role)
                .count()
            )

            self.stdout.write(
                f"  {role.libelle}: "
                f"{nombre} permissions"
            )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Initialisation terminée avec succès."
            )
        )

        self.stdout.write("")