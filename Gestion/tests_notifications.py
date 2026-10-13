"""Cycle de vie d'une notification : liste active -> clic -> historique.

Une notification non lue reste dans la liste active. Le clic appelle
ouvrir_notification : la vue renvoie le detail complet et marque la
notification comme lue, ce qui la fait basculer dans l'historique.

Ces tests vivent dans TestCase : la transaction est annulee apres
chacun, donc ils ecrivent dans Gestion_Ecole sans laisser de trace.
"""

from django.test import TestCase
from django.urls import reverse

from .models import (
    DestinataireNotification,
    Notification,
    Permission,
    Role,
    RolePermission,
    TypeNotification,
    Utilisateur,
    UtilisateurRole,
)


class NotificationHistoriqueTest(TestCase):
    """Le clic sur une notification doit la lire ET la deplacer en archive."""

    @classmethod
    def setUpTestData(cls):
        role_autorise = Role.objects.create(
            code="TEST_NOTIF",
            libelle="Notification de test",
            actif=True,
        )
        role_sans_droit = Role.objects.create(
            code="TEST_NOTIF_SANS_DROIT",
            libelle="Sans droit notification",
            actif=True,
        )

        permission, _ = Permission.objects.get_or_create(
            code="notification.consulter",
            defaults={"libelle": "Consulter les notifications"},
        )

        RolePermission.objects.create(
            role=role_autorise,
            permission=permission,
        )

        cls.utilisateur = Utilisateur.objects.create(
            nom="TEST",
            postnom="SECRETAIRE",
            prenom="Notification",
            email="test.notifications@example.test",
            actif=True,
        )
        UtilisateurRole.objects.create(
            utilisateur=cls.utilisateur,
            role=role_autorise,
            actif=True,
        )

        cls.utilisateur_sans_droit = Utilisateur.objects.create(
            nom="TEST",
            postnom="SANS_DROIT",
            prenom="Notification",
            email="test.notifications.sansdroit@example.test",
            actif=True,
        )
        UtilisateurRole.objects.create(
            utilisateur=cls.utilisateur_sans_droit,
            role=role_sans_droit,
            actif=True,
        )

        cls.type_notification = TypeNotification.objects.create(
            code="INFO",
            libelle="Information",
        )

        cls.notification = Notification.objects.create(
            type_notification=cls.type_notification,
            utilisateur_createur=cls.utilisateur,
            objet="Frais de scolarite",
            contenu="Le second acompte est verse le 30 novembre.",
            statut=Notification.ENVOYEE,
        )

        cls.destinataire = DestinataireNotification.objects.create(
            notification=cls.notification,
            utilisateur=cls.utilisateur,
        )

    def _connecter(self, utilisateur=None):
        session = self.client.session
        session["utilisateur_id"] = (
            utilisateur or self.utilisateur
        ).id
        session.save()

    def _ouvrir(self, destinataire_id=None):
        return self.client.post(
            reverse(
                "ouvrir_notification",
                args=[
                    destinataire_id
                    or self.destinataire.id
                ],
            )
        )

    # ---------------------------------------------------------------
    # LISTE ACTIVE
    # ---------------------------------------------------------------

    def test_liste_active_affiche_la_notification_non_lue(self):
        self._connecter()

        reponse = self.client.get(
            reverse("liste_notifications")
        )

        self.assertEqual(reponse.status_code, 200)

        contenu = reponse.content.decode()

        self.assertIn("Frais de scolarite", contenu)
        self.assertIn("Le second acompte", contenu)

    def test_liste_active_expose_la_variable_utilisee_par_le_template(self):
        """Le template boucle sur `notifications`, pas sur `destinataires`.

        Une variable absente se resout en liste vide : la page affiche
        « aucune notification » alors que la base en contient une.
        """
        self._connecter()

        reponse = self.client.get(
            reverse("liste_notifications")
        )

        self.assertEqual(
            list(reponse.context["notifications"]),
            [self.destinataire],
            "la liste active doit exposer les notifications non lues",
        )

    # ---------------------------------------------------------------
    # OUVERTURE : DETAIL + MARQUAGE LU
    # ---------------------------------------------------------------

    def test_ouvrir_renvoie_le_detail_du_message(self):
        self._connecter()

        reponse = self._ouvrir()

        self.assertEqual(reponse.status_code, 200)

        donnees = reponse.json()

        self.assertTrue(donnees["success"])

        detail = donnees["notification"]

        self.assertEqual(detail["objet"], "Frais de scolarite")
        self.assertEqual(
            detail["contenu"],
            "Le second acompte est verse le 30 novembre.",
        )
        self.assertEqual(detail["type_code"], "info")
        self.assertEqual(detail["type_libelle"], "Information")
        self.assertEqual(detail["id"], self.destinataire.id)

    def test_ouvrir_marque_la_notification_comme_lue(self):
        self._connecter()

        self._ouvrir()

        self.destinataire.refresh_from_db()

        self.assertTrue(
            self.destinataire.lu,
            "l'ouverture doit marquer la notification comme lue",
        )

    def test_ouvrir_decompte_le_restant(self):
        self._connecter()

        donnees = self._ouvrir().json()

        self.assertEqual(
            donnees["nb_non_lues"],
            0,
            "plus aucune notification active apres ouverture",
        )

    def test_la_notification_quitte_la_liste_active(self):
        self._connecter()

        self._ouvrir()

        reponse = self.client.get(
            reverse("liste_notifications")
        )

        self.assertEqual(
            list(reponse.context["notifications"]),
            [],
            "une notification lue ne doit plus rester dans la liste active",
        )

        self.assertNotIn(
            "Frais de scolarite",
            reponse.content.decode(),
        )

    # ---------------------------------------------------------------
    # HISTORIQUE
    # ---------------------------------------------------------------

    def test_historique_recupere_la_notification_cliquee(self):
        self._connecter()

        self._ouvrir()

        reponse = self.client.get(
            reverse("historique_notifications")
        )

        self.assertEqual(reponse.status_code, 200)

        self.assertEqual(
            list(reponse.context["notifications"]),
            [self.destinataire],
            "la notification lue doit se retrouver dans l'historique",
        )

        contenu = reponse.content.decode()

        self.assertIn("Frais de scolarite", contenu)
        self.assertIn(
            "Le second acompte est verse le 30 novembre.",
            contenu,
        )

    def test_historique_ignore_les_notifications_non_lues(self):
        self._connecter()

        reponse = self.client.get(
            reverse("historique_notifications")
        )

        self.assertEqual(
            list(reponse.context["notifications"]),
            [],
            "une notification jamais lue ne doit pas figurer a l'historique",
        )

    # ---------------------------------------------------------------
    # GARDE-FOUS
    # ---------------------------------------------------------------

    def test_ouvrir_refuse_un_get(self):
        self._connecter()

        reponse = self.client.get(
            reverse(
                "ouvrir_notification",
                args=[self.destinataire.id],
            )
        )

        self.assertEqual(reponse.status_code, 405)

        self.destinataire.refresh_from_db()

        self.assertFalse(self.destinataire.lu)

    def test_ouvrir_refuse_la_notification_d_un_autre(self):
        self._connecter()

        autre = Utilisateur.objects.create(
            nom="TEST",
            postnom="AUTRE",
            prenom="Notification",
            email="test.notifications.autre@example.test",
            actif=True,
        )
        UtilisateurRole.objects.create(
            utilisateur=autre,
            role=Role.objects.get(code="TEST_NOTIF"),
            actif=True,
        )

        notification_autre = Notification.objects.create(
            type_notification=self.type_notification,
            utilisateur_createur=autre,
            objet="Confidentiel",
            contenu="Message d'un autre compte.",
            statut=Notification.ENVOYEE,
        )
        destinataire_autre = DestinataireNotification.objects.create(
            notification=notification_autre,
            utilisateur=autre,
        )

        reponse = self._ouvrir(destinataire_autre.id)

        self.assertEqual(reponse.status_code, 404)

        destinataire_autre.refresh_from_db()

        self.assertFalse(
            destinataire_autre.lu,
            "on ne doit pas lire la notification d'un autre utilisateur",
        )

    def test_ouvrir_refuse_sans_permission(self):
        self._connecter(self.utilisateur_sans_droit)

        reponse = self._ouvrir()

        self.assertEqual(reponse.status_code, 403)

        self.destinataire.refresh_from_db()

        self.assertFalse(self.destinataire.lu)

    def test_historique_refuse_sans_permission(self):
        self._connecter(self.utilisateur_sans_droit)

        reponse = self.client.get(
            reverse("historique_notifications")
        )

        self.assertEqual(reponse.status_code, 302)

        self.assertNotIn(
            reverse("historique_notifications"),
            reponse.get("Location", ""),
            "un acces refuse ne doit pas ouvrir l'historique",
        )