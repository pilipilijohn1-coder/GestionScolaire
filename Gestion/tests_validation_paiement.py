"""Boucle de validation d'un paiement, de la tranche a la caisse.

Ces tests vivent dans TestCase : la transaction est annulee apres
chacun, donc ils ecrivent dans Gestion_Ecole sans laisser de trace.
"""

from datetime import time
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from . import views as vues
from .models import (
    Caisse,
    EntreeCaisse,
    FraisScolaires,
    Inscription,
    Paiement,
    Tranche,
    Utilisateur,
)


class ValidationPaiementTest(TestCase):
    """La validation doit etre l'unique passage de ENREGISTRE a VALIDE,
    et doit porter l'argent en caisse dans la meme transaction."""

    @classmethod
    def setUpTestData(cls):
        from .models import (
            AnneeScolaire,
            Classe,
            Eleve,
            Niveau,
            Role,
            RolePermission,
            UtilisateurRole,
        )

        role = Role.objects.create(
            code="TEST_COMPTABLE",
            libelle="Comptable de test",
            actif=True,
        )

        for code in (
            "paiement.enregistrer",
            "paiement.consulter",
            "paiement.valider",
            "paiement.annuler",
            "caisse.consulter",
            "caisse.enregistrer_entree",
        ):
            from .models import Permission

            permission, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"libelle": code},
            )
            RolePermission.objects.get_or_create(
                role=role,
                permission=permission,
            )

        cls.utilisateur = Utilisateur.objects.create(
            nom="TEST",
            postnom="COMPTABLE",
            prenom="Validation",
            email="test.comptable@example.test",
            actif=True,
        )
        UtilisateurRole.objects.create(
            utilisateur=cls.utilisateur,
            role=role,
            actif=True,
        )

        annee = AnneeScolaire.objects.create(
            libelle="2026-2027",
            date_debut="2026-09-01",
            date_fin="2027-07-31",
            statut=AnneeScolaire.ACTIVE,
        )
        niveau = Niveau.objects.create(
            code="6T",
            libelle="6e Test",
            ordre=90,
        )
        classe = Classe.objects.create(
            code="6T",
            libelle="6e Test",
            niveau=niveau,
            section=None,
            annee=annee,
        )
        eleve = Eleve.objects.create(
            matricule="TEST-VALID-001",
            nom="TEST",
            postnom="ELEVE",
            prenom="Validation",
            sexe="M",
            date_naissance="2015-05-05",
        )
        cls.inscription = Inscription.objects.create(
            eleve=eleve,
            classe=classe,
            annee=annee,
            statut=Inscription.ACTIVE,
        )

        frais = FraisScolaires.objects.create(
            annee=annee,
            libelle="Frais 6e Test",
            montant_total=Decimal("200.00"),
            actif=True,
        )
        cls.tranche_1 = Tranche.objects.create(
            frais=frais,
            numero=1,
            montant=Decimal("100.00"),
            date_echeance="2026-10-01",
        )
        cls.tranche_2 = Tranche.objects.create(
            frais=frais,
            numero=2,
            montant=Decimal("100.00"),
            date_echeance="2027-01-10",
        )

        cls.caisse = Caisse.objects.create(
            libelle="Caisse de test",
            heure_ouverture=time(8, 0),
            heure_fermeture=time(17, 0),
            statut=Caisse.OUVERTE,
        )

    def _connecter(self):
        session = self.client.session
        session["utilisateur_id"] = self.utilisateur.id
        session.save()

    def _enregistrer_paiement(self, montant="100.00"):
        self._connecter()
        return self.client.post(
            reverse("encaisser_paiement"),
            {
                "inscription_id": self.inscription.id,
                "tranche_id": self.tranche_1.id,
                "montant": montant,
            },
        )

    # ---------------------------------------------------------------

    def test_encaissement_cree_un_paiement_enregistre_pas_valide(self):
        self._enregistrer_paiement()

        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.assertEqual(paiement.statut, Paiement.ENREGISTRE)
        self.assertEqual(
            vues._reste_tranche(self.tranche_1),
            Decimal("100.00"),
            "un paiement non valide ne doit pas solder la tranche",
        )

    def test_validation_passe_le_paiement_a_valide(self):
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )

        paiement.refresh_from_db()

        self.assertEqual(paiement.statut, Paiement.VALIDE)
        self.assertEqual(paiement.valide_par, self.utilisateur)

    def test_validation_solde_la_tranche(self):
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )

        self.assertEqual(
            vues._reste_tranche(self.tranche_1),
            Decimal("0.00"),
            "la tranche doit etre soldee par le paiement valide",
        )

    def test_validation_porte_largent_en_caisse(self):
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )

        entree = EntreeCaisse.objects.get(paiement=paiement)

        self.assertEqual(entree.caisse, self.caisse)
        self.assertEqual(entree.montant, Decimal("100.00"))
        self.assertEqual(entree.enregistre_par, self.utilisateur)

    def test_double_validation_ne_double_paie_pas(self):
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )
        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )

        self.assertEqual(
            EntreeCaisse.objects.filter(paiement=paiement).count(),
            1,
            "un second passage ne doit pas creer une seconde entree",
        )

    def test_sans_caisse_ouverte_le_paiement_reste_valide(self):
        """Un versement recu entre en caisse meme sans caisse ouverte.

        Ce test verrouillait le comportement inverse : l'absence de
        caisse ouverte laissait le paiement VALIDE sans aucune entree,
        et l'argent disparaissait du solde sans moyen de le reintegrer
        (la validation ne se rejoue pas une fois le statut pose).
        L'entree desactivee doit maintenant s'ouvrir d'elle-meme.
        """
        self.caisse.statut = Caisse.FERMEE
        self.caisse.save()

        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )

        paiement.refresh_from_db()

        self.assertEqual(
            paiement.statut,
            Paiement.VALIDE,
            "le versement recu ne doit pas dependre d'une caisse",
        )

        entree = EntreeCaisse.objects.filter(paiement=paiement).first()

        self.assertIsNotNone(
            entree,
            "un montant recu doit toujours apparaitre en caisse",
        )
        self.assertEqual(
            entree.montant,
            paiement.montant,
            "l'entree doit porter le montant exact du paiement",
        )

    def test_porter_en_caisse_repare_un_paiement_oublie(self):
        """Un paiement valide sans entree peut etre porte en caisse."""
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )

        # On simule le paiement anterieur a la correction : valide,
        # maisAucune entree.
        EntreeCaisse.objects.filter(paiement=paiement).delete()

        self.client.post(
            reverse("porter_en_caisse", args=[paiement.id])
        )

        self.assertTrue(
            EntreeCaisse.objects.filter(paiement=paiement).exists(),
            "le rattrapage doit recreer l'entree manquante",
        )

    def test_porter_en_caisse_refuse_un_paiement_non_valide(self):
        """Un paiement enregistre n'est pas porte en caisse."""
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.client.post(
            reverse("porter_en_caisse", args=[paiement.id])
        )

        self.assertFalse(
            EntreeCaisse.objects.filter(paiement=paiement).exists(),
            "seul un paiement valide peut etre porte en caisse",
        )

    def test_annulation_retire_lentree_de_caisse(self):
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )
        self.client.post(
            reverse("annuler_paiement", args=[paiement.id])
        )

        paiement.refresh_from_db()

        self.assertEqual(paiement.statut, Paiement.ANNULE)
        self.assertIsNone(paiement.valide_par)
        self.assertFalse(
            EntreeCaisse.objects.filter(paiement=paiement).exists(),
            "un paiement annule ne doit pas laisser d'entree en caisse",
        )
        self.assertEqual(
            vues._reste_tranche(self.tranche_1),
            Decimal("100.00"),
            "l'annulation doit rouvrir la tranche",
        )

    def test_entree_refusee_annule_toute_la_validation(self):
        """ Une ecriture de caisse refusee ne doit pas laisser un paiement
        valide sans argent comptabilise. Les deux font partie de la meme
        operation. """
        from unittest.mock import patch

        from django.core.exceptions import ValidationError

        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)

        with patch.object(
            EntreeCaisse,
            "full_clean",
            side_effect=ValidationError("Caisse refusee."),
        ):
            reponse = self.client.post(
                reverse("valider_paiement", args=[paiement.id])
            )

        paiement.refresh_from_db()

        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(
            paiement.statut,
            Paiement.ENREGISTRE,
            "un paiement ne doit pas rester valide sans son entree",
        )
        self.assertIsNone(paiement.valide_par)
        self.assertEqual(
            EntreeCaisse.objects.count(),
            0,
            "l'entree refusee ne doit pas etre conservee",
        )

    # ---------------------------------------------------------------
    # RENDU : le tableau doit rester affichable dans les trois etats
    # ---------------------------------------------------------------
    def test_liste_des_paiements_se_rend_dans_chaque_etat(self):
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)
        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )
        self.client.post(
            reverse("annuler_paiement", args=[paiement.id])
        )

        self._connecter()

        for statut in Paiement.STATUT_CHOICES:
            with self.subTest(statut=statut[0]):
                reponse = self.client.get(
                    reverse("liste_paiements"),
                    {"statut": statut[0]},
                )

                self.assertEqual(reponse.status_code, 200)

        # Le libelle de la tranche venait d'un champ inexistant :
        # la colonne restait vide sans lever la moindre erreur.
        contenu = self.client.get(reverse("liste_paiements")).content.decode()

        self.assertIn("Frais 6e Test", contenu)
        self.assertIn("Tranche n° 1", contenu)

    def test_detail_paiement_se_rend(self):
        self._enregistrer_paiement()
        paiement = Paiement.objects.get(tranche=self.tranche_1)
        self.client.post(
            reverse("valider_paiement", args=[paiement.id])
        )
        self._connecter()

        reponse = self.client.get(
            reverse("detail_paiement", args=[paiement.id])
        )

        self.assertEqual(reponse.status_code, 200)