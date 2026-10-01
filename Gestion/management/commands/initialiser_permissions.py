from django.core.management.base import BaseCommand
from Gestion.models import Role, Permission, RolePermission, TypeNotification


class Command(BaseCommand):
    help = "Initialise les rôles, permissions et associations du système."

    def handle(self, *args, **options):

        # ============================================================
        # 1. MODULES / PERMISSIONS
        # ============================================================

        permissions = {

            # --------------------------------------------------------
            # UTILISATEURS
            # --------------------------------------------------------
            "UTILISATEUR_CONSULTER": "Consulter les utilisateurs",
            "UTILISATEUR_CREER": "Créer un utilisateur",
            "UTILISATEUR_MODIFIER": "Modifier un utilisateur",
            "UTILISATEUR_DESACTIVER": "Désactiver un utilisateur",
            "UTILISATEUR_ACTIVER": "Activer un utilisateur",
            "UTILISATEUR_ATTRIBUER_ROLE": "Attribuer un rôle",
            "UTILISATEUR_RETIRER_ROLE": "Retirer un rôle",

            # --------------------------------------------------------
            # ELEVES
            # --------------------------------------------------------
            "ELEVE_CONSULTER": "Consulter les élèves",
            "ELEVE_CREER": "Créer un élève",
            "ELEVE_MODIFIER": "Modifier un élève",
            "ELEVE_DESACTIVER": "Désactiver un élève",

            # --------------------------------------------------------
            # RESPONSABLES
            # --------------------------------------------------------
            "RESPONSABLE_CONSULTER": "Consulter les responsables",
            "RESPONSABLE_CREER": "Créer un responsable",
            "RESPONSABLE_MODIFIER": "Modifier un responsable",
            "RESPONSABLE_DESACTIVER": "Désactiver un responsable",

            # --------------------------------------------------------
            # INSCRIPTIONS
            # --------------------------------------------------------
            "INSCRIPTION_CONSULTER": "Consulter les inscriptions",
            "INSCRIPTION_CREER": "Créer une inscription",
            "INSCRIPTION_MODIFIER": "Modifier une inscription",
            "INSCRIPTION_ANNULER": "Annuler une inscription",
            "INSCRIPTION_VALIDER": "Valider une inscription",
            "INSCRIPTION_REINSCRIRE": "Réinscrire un élève",

            # --------------------------------------------------------
            # ENSEIGNANTS
            # --------------------------------------------------------
            "ENSEIGNANT_CONSULTER": "Consulter les enseignants",
            "ENSEIGNANT_CREER": "Créer un enseignant",
            "ENSEIGNANT_MODIFIER": "Modifier un enseignant",
            "ENSEIGNANT_DESACTIVER": "Désactiver un enseignant",

            # --------------------------------------------------------
            # AFFECTATIONS
            # --------------------------------------------------------
            "AFFECTATION_CONSULTER": "Consulter les affectations",
            "AFFECTATION_CREER": "Créer une affectation",
            "AFFECTATION_MODIFIER": "Modifier une affectation",
            "AFFECTATION_DESACTIVER": "Désactiver une affectation",

            # --------------------------------------------------------
            # TITULARISATION
            # --------------------------------------------------------
            "TITULARISATION_CONSULTER": "Consulter les titularisations",
            "TITULARISATION_CREER": "Créer une titularisation",
            "TITULARISATION_MODIFIER": "Modifier une titularisation",
            "TITULARISATION_ANNULER": "Annuler une titularisation",

            # --------------------------------------------------------
            # PEDAGOGIE
            # --------------------------------------------------------
            "MATIERE_CONSULTER": "Consulter les matières",
            "MATIERE_CREER": "Créer une matière",
            "MATIERE_MODIFIER": "Modifier une matière",

            "CLASSE_CONSULTER": "Consulter les classes",
            "CLASSE_CREER": "Créer une classe",
            "CLASSE_MODIFIER": "Modifier une classe",

            # --------------------------------------------------------
            # NOTES / EVALUATIONS
            # --------------------------------------------------------
            "NOTE_CONSULTER": "Consulter les notes",
            "NOTE_SAISIR": "Saisir une note",
            "NOTE_MODIFIER": "Modifier une note",
            "NOTE_ANNULER": "Annuler une note",
            "NOTE_VERROUILLER": "Verrouiller une note",
            "NOTE_DEVERROUILLER": "Déverrouiller une note",

            "EVALUATION_CONSULTER": "Consulter les évaluations",
            "EVALUATION_CREER": "Créer une évaluation",
            "EVALUATION_MODIFIER": "Modifier une évaluation",
            "EVALUATION_VERROUILLER": "Verrouiller une évaluation",

            # --------------------------------------------------------
            # EXAMENS
            # --------------------------------------------------------
            "EXAMEN_CONSULTER": "Consulter les examens",
            "EXAMEN_CREER": "Créer un examen",
            "EXAMEN_MODIFIER": "Modifier un examen",
            "EXAMEN_VERROUILLER": "Verrouiller un examen",

            "RESULTAT_EXAMEN_CONSULTER": "Consulter les résultats d'examen",
            "RESULTAT_EXAMEN_SAISIR": "Saisir un résultat d'examen",
            "RESULTAT_EXAMEN_MODIFIER": "Modifier un résultat d'examen",

            # --------------------------------------------------------
            # RESULTATS
            # --------------------------------------------------------
            "RESULTAT_PERIODE_CONSULTER": "Consulter les résultats de période",
            "RESULTAT_SEMESTRE_CONSULTER": "Consulter les résultats de semestre",
            "RESULTAT_ANNUEL_CONSULTER": "Consulter les résultats annuels",
            "RESULTAT_CALCULER": "Calculer les résultats",

            # --------------------------------------------------------
            # PONDERATIONS
            # --------------------------------------------------------
            "PONDERATION_CONSULTER": "Consulter les pondérations",
            "PONDERATION_CREER": "Créer une pondération",
            "PONDERATION_MODIFIER": "Modifier une pondération",

            # --------------------------------------------------------
            # BULLETINS
            # --------------------------------------------------------
            "BULLETIN_CONSULTER": "Consulter les bulletins",
            "BULLETIN_GENERER": "Générer un bulletin",
            "BULLETIN_VALIDER": "Valider un bulletin",
            "BULLETIN_VERROUILLER": "Verrouiller un bulletin",
            "BULLETIN_ANNULER": "Annuler un bulletin",

            # --------------------------------------------------------
            # PROCLAMATIONS
            # --------------------------------------------------------
            "PROCLAMATION_CONSULTER": "Consulter les proclamations",
            "PROCLAMATION_CREER": "Créer une proclamation",
            "PROCLAMATION_VALIDER": "Valider une proclamation",
            "PROCLAMATION_ANNULER": "Annuler une proclamation",

            # --------------------------------------------------------
            # PRESENCES
            # --------------------------------------------------------
            "PRESENCE_CONSULTER": "Consulter les présences",
            "PRESENCE_SAISIR": "Saisir une présence",
            "PRESENCE_MODIFIER": "Modifier une présence",
            "PRESENCE_JUSTIFIER": "Justifier une absence",

            # --------------------------------------------------------
            # DISCIPLINE
            # --------------------------------------------------------
            "DISCIPLINE_CONSULTER": "Consulter les informations disciplinaires",
            "DISCIPLINE_GERER": "Gérer la discipline",
            "ALERTE_ABSENCE_CREER": "Créer une alerte d'absence",

            # --------------------------------------------------------
            # FINANCES
            # --------------------------------------------------------
            "FRAIS_CONSULTER": "Consulter les frais",
            "FRAIS_CREER": "Créer les frais",
            "FRAIS_MODIFIER": "Modifier les frais",

            "TRANCHE_CONSULTER": "Consulter les tranches",
            "TRANCHE_CREER": "Créer une tranche",
            "TRANCHE_MODIFIER": "Modifier une tranche",

            "PAIEMENT_CONSULTER": "Consulter les paiements",
            "PAIEMENT_ENREGISTRER": "Enregistrer un paiement",
            "PAIEMENT_MODIFIER": "Modifier un paiement",
            "PAIEMENT_VALIDER": "Valider un paiement",
            "PAIEMENT_ANNULER": "Annuler un paiement",

            "RECU_CONSULTER": "Consulter les reçus",
            "RECU_GENERER": "Générer un reçu",

            "CAISSE_CONSULTER": "Consulter la caisse",
            "CAISSE_OUVRIR": "Ouvrir la caisse",
            "CAISSE_FERMER": "Fermer la caisse",
            "ENTREE_CAISSE_ENREGISTRER": "Enregistrer une entrée de caisse",
            "SORTIE_CAISSE_ENREGISTRER": "Enregistrer une sortie de caisse",
            "SORTIE_CAISSE_VALIDER": "Valider une sortie de caisse",

            # --------------------------------------------------------
            # AUTORISATIONS
            # --------------------------------------------------------
            "AUTORISATION_CONSULTER": "Consulter les demandes d'autorisation",
            "AUTORISATION_DEMANDER": "Demander une autorisation",
            "AUTORISATION_APPROUVER": "Approuver une autorisation",
            "AUTORISATION_REFUSER": "Refuser une autorisation",

            # --------------------------------------------------------
            # NOTIFICATIONS
            # --------------------------------------------------------
            "NOTIFICATION_CONSULTER": "Consulter les notifications",
            "NOTIFICATION_CREER": "Créer une notification",
            "NOTIFICATION_ENVOYER": "Envoyer une notification",
            "NOTIFICATION_REENVOYER": "Renvoyer une notification",

            # --------------------------------------------------------
            # AUDIT
            # --------------------------------------------------------
            "AUDIT_CONSULTER": "Consulter l'historique",
            "AUDIT_EXPORTER": "Exporter l'historique",

            "ANOMALIE_CONSULTER": "Consulter les anomalies",
            "ANOMALIE_TRAITER": "Traiter une anomalie",
        }

        # ============================================================
        # 2. CREATION DES PERMISSIONS
        # ============================================================

        permission_objects = {}

        for code, libelle in permissions.items():

            permission, created = Permission.objects.get_or_create(
                code=code,
                defaults={
                    "libelle": libelle
                }
            )

            # Mise à jour du libellé si nécessaire
            if permission.libelle != libelle:
                permission.libelle = libelle
                permission.save(update_fields=["libelle"])

            permission_objects[code] = permission

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(permission_objects)} permissions disponibles."
            )
        )

        # ============================================================
        # 3. ROLES
        # ============================================================

        roles = {
            "ADMIN": "Administrateur",
            "DIRECTEUR": "Directeur",
            "PREFET": "Préfet des études",
            "PROMOTEUR": "Promoteur",
            "SECRETAIRE": "Secrétaire",
            "ENSEIGNANT": "Enseignant",
            "DIRECTEUR_DISCIPLINE": "Directeur de discipline",
            "COMPTABLE": "Comptable",
        }

        role_objects = {}

        for code, libelle in roles.items():

            role, created = Role.objects.get_or_create(
                code=code,
                defaults={
                    "libelle": libelle,
                    "actif": True,
                }
            )

            role_objects[code] = role

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(role_objects)} rôles disponibles."
            )
        )

        # ============================================================
        # 4. ASSOCIATION DES ROLES AUX PERMISSIONS
        # ============================================================

        role_permissions = {

            # ========================================================
            # ADMINISTRATEUR
            # ========================================================

            "ADMIN": [
                "UTILISATEUR_CONSULTER",
                "UTILISATEUR_CREER",
                "UTILISATEUR_MODIFIER",
                "UTILISATEUR_DESACTIVER",
                "UTILISATEUR_ACTIVER",
                "UTILISATEUR_ATTRIBUER_ROLE",
                "UTILISATEUR_RETIRER_ROLE",

                "ELEVE_CONSULTER",
                "ELEVE_CREER",
                "ELEVE_MODIFIER",
                "ELEVE_DESACTIVER",

                "RESPONSABLE_CONSULTER",
                "RESPONSABLE_CREER",
                "RESPONSABLE_MODIFIER",
                "RESPONSABLE_DESACTIVER",

                "INSCRIPTION_CONSULTER",
                "INSCRIPTION_CREER",
                "INSCRIPTION_MODIFIER",

                "ENSEIGNANT_CONSULTER",
                "ENSEIGNANT_CREER",
                "ENSEIGNANT_MODIFIER",

                "AFFECTATION_CONSULTER",
                "AFFECTATION_CREER",
                "AFFECTATION_MODIFIER",
                "AFFECTATION_DESACTIVER",

                "TITULARISATION_CONSULTER",
                "TITULARISATION_CREER",
                "TITULARISATION_MODIFIER",
                "TITULARISATION_ANNULER",

                "MATIERE_CONSULTER",
                "MATIERE_CREER",
                "MATIERE_MODIFIER",

                "CLASSE_CONSULTER",
                "CLASSE_CREER",
                "CLASSE_MODIFIER",

                "PONDERATION_CONSULTER",

                "AUDIT_CONSULTER",
                "AUDIT_EXPORTER",

                "ANOMALIE_CONSULTER",
                "ANOMALIE_TRAITER",

                "AUTORISATION_CONSULTER",
                "AUTORISATION_DEMANDER",
            ],

            # ========================================================
            # DIRECTEUR
            # ========================================================

            "DIRECTEUR": [
                "UTILISATEUR_CONSULTER",

                "ELEVE_CONSULTER",
                "RESPONSABLE_CONSULTER",

                "INSCRIPTION_CONSULTER",
                "INSCRIPTION_VALIDER",

                "ENSEIGNANT_CONSULTER",

                "AFFECTATION_CONSULTER",
                "AFFECTATION_CREER",
                "AFFECTATION_MODIFIER",
                "AFFECTATION_DESACTIVER",

                "TITULARISATION_CONSULTER",
                "TITULARISATION_CREER",

                "CLASSE_CONSULTER",
                "MATIERE_CONSULTER",
                "MATIERE_CREER",
                "MATIERE_MODIFIER",

                "NOTE_CONSULTER",
                "EVALUATION_CONSULTER",
                "EXAMEN_CONSULTER",

                "RESULTAT_PERIODE_CONSULTER",
                "RESULTAT_SEMESTRE_CONSULTER",
                "RESULTAT_ANNUEL_CONSULTER",

                "BULLETIN_CONSULTER",
                "BULLETIN_VALIDER",

                "PROCLAMATION_CONSULTER",
                "PROCLAMATION_VALIDER",

                "PRESENCE_CONSULTER",

                "DISCIPLINE_CONSULTER",

                "PONDERATION_CONSULTER",

                "AUTORISATION_CONSULTER",
                "AUTORISATION_APPROUVER",
                "AUTORISATION_REFUSER",

                "AUDIT_CONSULTER",
                "ANOMALIE_CONSULTER",
            ],

            # ========================================================
            # PREFET
            # ========================================================

            "PREFET": [
                "ELEVE_CONSULTER",
                "RESPONSABLE_CONSULTER",

                "INSCRIPTION_CONSULTER",
                "INSCRIPTION_VALIDER",
                "INSCRIPTION_REINSCRIRE",

                "ENSEIGNANT_CONSULTER",

                "AFFECTATION_CONSULTER",
                "AFFECTATION_CREER",
                "AFFECTATION_MODIFIER",

                "TITULARISATION_CONSULTER",
                "TITULARISATION_CREER",
                "TITULARISATION_MODIFIER",

                "CLASSE_CONSULTER",
                "MATIERE_CONSULTER",

                "NOTE_CONSULTER",
                "EVALUATION_CONSULTER",
                "EXAMEN_CONSULTER",

                "RESULTAT_PERIODE_CONSULTER",
                "RESULTAT_SEMESTRE_CONSULTER",
                "RESULTAT_ANNUEL_CONSULTER",
                "RESULTAT_CALCULER",

                "PONDERATION_CONSULTER",
                "PONDERATION_CREER",
                "PONDERATION_MODIFIER",

                "BULLETIN_CONSULTER",
                "BULLETIN_GENERER",
                "BULLETIN_VALIDER",
                "BULLETIN_VERROUILLER",

                "PROCLAMATION_CONSULTER",
                "PROCLAMATION_CREER",
                "PROCLAMATION_VALIDER",

                "PRESENCE_CONSULTER",

                "AUTORISATION_CONSULTER",
                "AUTORISATION_APPROUVER",
                "AUTORISATION_REFUSER",

                "AUDIT_CONSULTER",
                "ANOMALIE_CONSULTER",
            ],

            # ========================================================
            # PROMOTEUR
            # ========================================================

            "PROMOTEUR": [
                "ELEVE_CONSULTER",
                "INSCRIPTION_CONSULTER",
                "ENSEIGNANT_CONSULTER",

                "RESULTAT_ANNUEL_CONSULTER",

                "BULLETIN_CONSULTER",
                "PROCLAMATION_CONSULTER",

                "PRESENCE_CONSULTER",

                "FRAIS_CONSULTER",
                "PAIEMENT_CONSULTER",
                "RECU_CONSULTER",

                "CAISSE_CONSULTER",

                "AUDIT_CONSULTER",
            ],

            # ========================================================
            # SECRETAIRE
            # ========================================================

            "SECRETAIRE": [
                "ELEVE_CONSULTER",
                "ELEVE_CREER",
                "ELEVE_MODIFIER",

                "RESPONSABLE_CONSULTER",
                "RESPONSABLE_CREER",
                "RESPONSABLE_MODIFIER",

                "INSCRIPTION_CONSULTER",
                "INSCRIPTION_CREER",
                "INSCRIPTION_MODIFIER",
                "INSCRIPTION_REINSCRIRE",

                "ENSEIGNANT_CONSULTER",

                "CLASSE_CONSULTER",

                "BULLETIN_CONSULTER",

                "PRESENCE_CONSULTER",
            ],

            # ========================================================
            # ENSEIGNANT
            # ========================================================

            "ENSEIGNANT": [
                "ELEVE_CONSULTER",

                "CLASSE_CONSULTER",
                "MATIERE_CONSULTER",

                "NOTE_CONSULTER",
                "NOTE_SAISIR",
                "NOTE_MODIFIER",

                "EVALUATION_CONSULTER",
                "EVALUATION_CREER",
                "EVALUATION_MODIFIER",

                "EXAMEN_CONSULTER",

                "RESULTAT_EXAMEN_CONSULTER",

                "PRESENCE_CONSULTER",
                "PRESENCE_SAISIR",

                "BULLETIN_CONSULTER",
            ],

            # ========================================================
            # DIRECTEUR DE DISCIPLINE
            # ========================================================

            "DIRECTEUR_DISCIPLINE": [
                "ELEVE_CONSULTER",
                "INSCRIPTION_CONSULTER",

                "CLASSE_CONSULTER",

                "PRESENCE_CONSULTER",
                "PRESENCE_MODIFIER",
                "PRESENCE_JUSTIFIER",

                "DISCIPLINE_CONSULTER",
                "DISCIPLINE_GERER",

                "ALERTE_ABSENCE_CREER",

                "BULLETIN_CONSULTER",
            ],

            # ========================================================
            # COMPTABLE
            # ========================================================

            "COMPTABLE": [
                "ELEVE_CONSULTER",
                "INSCRIPTION_CONSULTER",

                "FRAIS_CONSULTER",
                "FRAIS_CREER",
                "FRAIS_MODIFIER",

                "TRANCHE_CONSULTER",
                "TRANCHE_CREER",
                "TRANCHE_MODIFIER",

                "PAIEMENT_CONSULTER",
                "PAIEMENT_ENREGISTRER",
                "PAIEMENT_MODIFIER",

                "RECU_CONSULTER",
                "RECU_GENERER",

                "CAISSE_CONSULTER",
                "ENTREE_CAISSE_ENREGISTRER",

                "SORTIE_CAISSE_ENREGISTRER",
            ],
        }

        # ============================================================
        # 5. CREATION DES ASSOCIATIONS
        # ============================================================

        total_associations = 0

        for role_code, permission_codes in role_permissions.items():

            role = role_objects[role_code]

            for permission_code in permission_codes:

                permission = permission_objects.get(permission_code)

                if not permission:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Permission inconnue : {permission_code}"
                        )
                    )
                    continue

                RolePermission.objects.get_or_create(
                    role=role,
                    permission=permission,
                )

                total_associations += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{total_associations} associations rôle/permission traitées."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Initialisation des permissions terminée avec succès."
            )
        )

        # ============================================================
        # 4. TYPES DE NOTIFICATION
        # ============================================================

        types_notification = [
            ("SUCCESS", "Succès"),
            ("ERROR", "Erreur"),
            ("WARNING", "Avertissement"),
            ("INFO", "Information"),
        ]

        total_types = 0

        for code, libelle in types_notification:
            type_notif, created = (
                TypeNotification.objects.get_or_create(
                    code=code,
                    defaults={"libelle": libelle},
                )
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Type de notification créé : {code}"
                    )
                )

            total_types += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{total_types} types de notification traités."
            )
        )
