import json
import re
import unicodedata

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import IntegrityError
from django.http import JsonResponse
from django.urls import reverse

from Gestion.permissions.base import utilisateur_a_permission

from .models import Affectation, AffectationMatiere, AnneeScolaire, BilletInscription, Caisse, ConfigurationHoraire, CreneauHoraire, EntreeCaisse, Horaire, Matiere, Niveau, PonderationMatiere, RepartitionHoraire, ResponsabiliteScolaire, Section, Titularisation, Eleve, Inscription, ResultatPeriode, Periode, Semestre, Evaluation, Examen
from django.core.exceptions import ValidationError
from .forms import AffectationForm, AffectationMatiereForm, AnneeScolaireForm, ClasseForm, ConfigurationHoraireForm, EnseignantForm, HoraireForm, MatiereForm, NiveauForm, RepartitionHoraireForm, TitularisationForm
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from Gestion.decorators import permission_requise, role_requis
from Gestion.historique import enregistrer_historique
from Gestion.permissions.decorators import permission_required
from django.db.models import Q, Count, Sum
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .decorators import permission_requise
from .historique import enregistrer_historique
from django.shortcuts import get_object_or_404, redirect, render
from .models import AnneeScolaire, CompteUtilisateur, Eleve
from .service.authentification import (
    authentifier,
)
from .models import (
    Utilisateur,
    CompteUtilisateur,
    UtilisateurRole,
    Eleve,
    Enseignant,
    Classe,
    HistoriqueAction,
    DemandeAutorisation,
    Anomalie,
    Role,
    Notification,
    DestinataireNotification,
    TypeNotification,
)
from .service.notification import (
    notifications_pour_utilisateur,
    nb_notifications_non_lues,
    marquer_comme_lue,
    message_vers_notification,
    notification_utilisateur,
)

# ============================================================
# AUTHENTIFICATION
# ============================================================

# ============================================================
# ROUTAGE PAR ROLE
# ============================================================

ROLES_TABLEAU_DE_BORD = (
    ("ADMIN", "dashboard_admin"),
    ("DIRECTEUR", "dashboard_directeur"),
    ("PREFET", "dashboard_prefet"),
    ("SECRETAIRE", "dashboard_secretaire"),
    ("ENSEIGNANT", "dashboard_enseignant"),
    ("PROMOTEUR", "dashboard_promoteur"),
    ("DIRECTEUR_DISCIPLINE", "dashboard_discipline"),
    ("COMPTABLE", "dashboard_comptable"),
)


def nom_tableau_de_bord(codes_roles):
    """Retourne le nom de route du tableau de bord correspondant au role.

    Les roles sont testes dans l'ordre de priorite de ROLES_TABLEAU_DE_BORD.
    Retourne None si aucun tableau de bord n'est associe.
    """
    codes_roles = codes_roles or []
    for code, nom_route in ROLES_TABLEAU_DE_BORD:
        if code in codes_roles:
            return nom_route
    return None


def connexion(request):

    if request.method == "POST":

        login = request.POST.get(
            "login",
            ""
        ).strip()

        mot_de_passe = request.POST.get(
            "mot_de_passe",
            ""
        )

        # =====================================================
        # 1. VÉRIFICATION DES CHAMPS
        # =====================================================

        if not login or not mot_de_passe:

            message_vers_notification(request, 'ERROR', "Veuillez remplir tous les champs.", "Veuillez remplir tous les champs.")

            return render(
                request,
                "connexion.html"
            )

        # =====================================================
        # 2. RECHERCHE DU COMPTE
        # =====================================================

        try:

            compte = (
                CompteUtilisateur.objects
                .select_related("utilisateur")
                .get(login=login)
            )

        except CompteUtilisateur.DoesNotExist:

            message_vers_notification(request, 'ERROR', "Identifiants incorrects.", "Identifiants incorrects.")

            return render(
                request,
                "connexion.html"
            )

        utilisateur = compte.utilisateur

        # =====================================================
        # 3. VÉRIFICATION DE L'ÉTAT DE L'UTILISATEUR
        # =====================================================

        if not utilisateur.actif:

            message_vers_notification(request, 'ERROR', "Votre compte est désactivé. "
                "Veuillez contacter l'administration.", "Votre compte est désactivé. "
                "Veuillez contacter l'administration.")

            return render(
                request,
                "connexion.html"
            )

        # =====================================================
        # 4. VÉRIFICATION DU VERROUILLAGE DU COMPTE
        # =====================================================

        maintenant = timezone.now()

        if compte.verrouille_jusqu_a:

            # Le compte est encore verrouillé
            if compte.verrouille_jusqu_a > maintenant:

                message_vers_notification(request, 'ERROR', "Votre compte est temporairement verrouillé. "
                    "Veuillez réessayer plus tard.", "Votre compte est temporairement verrouillé. "
                    "Veuillez réessayer plus tard.")

                return render(
                    request,
                    "connexion.html"
                )

            # ---------------------------------------------
            # Le délai de verrouillage est terminé
            # ---------------------------------------------

            compte.verrouille_jusqu_a = None
            compte.echecs_connexion = 0

            compte.save(
                update_fields=[
                    "verrouille_jusqu_a",
                    "echecs_connexion",
                ]
            )

        # =====================================================
        # 5. VÉRIFICATION DU MOT DE PASSE
        # =====================================================

        mot_de_passe_correct = check_password(
            mot_de_passe,
            compte.mot_de_passe_hash
        )

        if not mot_de_passe_correct:

            compte.echecs_connexion += 1

            # ---------------------------------------------
            # VERROUILLAGE APRÈS 5 ÉCHECS
            # ---------------------------------------------

            if compte.echecs_connexion >= 5:

                compte.verrouille_jusqu_a = (
                    maintenant + timedelta(minutes=15)
                )

                compte.save(
                    update_fields=[
                        "echecs_connexion",
                        "verrouille_jusqu_a",
                    ]
                )

                message_vers_notification(request, 'ERROR', "Votre compte a été temporairement verrouillé "
                    "après plusieurs tentatives incorrectes. "
                    "Veuillez réessayer dans 15 minutes.", "Votre compte a été temporairement verrouillé "
                    "après plusieurs tentatives incorrectes. "
                    "Veuillez réessayer dans 15 minutes.")

            else:

                compte.save(
                    update_fields=[
                        "echecs_connexion"
                    ]
                )

                tentatives_restantes = (
                    5 - compte.echecs_connexion
                )

                message_vers_notification(request, 'ERROR', f"Identifiants incorrects. "
                    f"Il vous reste "
                    f"{tentatives_restantes} tentative(s) "
                    f"avant le verrouillage du compte.", f"Identifiants incorrects. "
                    f"Il vous reste "
                    f"{tentatives_restantes} tentative(s) "
                    f"avant le verrouillage du compte.")

            return render(
                request,
                "connexion.html"
            )

        # =====================================================
        # 6. CONNEXION RÉUSSIE
        # =====================================================

        roles = (
            UtilisateurRole.objects
            .filter(
                utilisateur=utilisateur,
                actif=True,
                role__actif=True,
            )
            .select_related("role")
        )

        codes_roles = [
            attribution.role.code
            for attribution in roles
        ]

        # =====================================================
        # 7. CRÉATION DE LA SESSION
        # =====================================================

        request.session["utilisateur_id"] = utilisateur.id

        request.session["utilisateur_nom"] = (
            f"{utilisateur.prenom} "
            f"{utilisateur.nom}"
        )

        request.session["roles"] = codes_roles

        # =====================================================
        # 8. MISE À JOUR DU COMPTE
        # =====================================================

        compte.dernier_login = maintenant
        compte.echecs_connexion = 0
        compte.verrouille_jusqu_a = None

        compte.save(
            update_fields=[
                "dernier_login",
                "echecs_connexion",
                "verrouille_jusqu_a",
            ]
        )

        # =====================================================
        # 9. REDIRECTION SELON LE RÔLE
        # =====================================================

        nom_route = nom_tableau_de_bord(codes_roles)

        if nom_route:
            return redirect(nom_route)

        # =========================================================
        # 10. AUCUN TABLEAU DE BORD ASSOCIÉ
        # =========================================================

        message_vers_notification(request, 'WARNING', "Votre compte possède un rôle, mais aucun "
            "tableau de bord n'est encore associé.", "Votre compte possède un rôle, mais aucun "
            "tableau de bord n'est encore associé.")

        return redirect("dashboard_admin")

    # =========================================================
    # GET
    # =========================================================

    return render(
        request,
        "connexion.html"
    )
    
# ============================================================
# DECONNEXION
# ============================================================

def deconnexion(request):

    request.session.flush()

    message_vers_notification(request, 'SUCCESS', "Vous êtes maintenant déconnecté.", "Vous êtes maintenant déconnecté.")

    return redirect("connexion")


# ============================================================
# DASHBOARD ADMINISTRATEUR
# ============================================================
@role_requis("ADMIN")
def dashboard_admin(request):

    # --------------------------------------------------------
    # 1. Vérification de session
    # --------------------------------------------------------

    utilisateur_id = request.session.get(
        "utilisateur_id"
    )

    if not utilisateur_id:

        return redirect("connexion")


    # --------------------------------------------------------
    # 2. Récupération de l'utilisateur
    # --------------------------------------------------------

    try:

        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )

    except Utilisateur.DoesNotExist:

        request.session.flush()

        message_vers_notification(request, 'ERROR', "La session utilisateur est invalide.", "La session utilisateur est invalide.")

        return redirect("connexion")


    # --------------------------------------------------------
    # 3. Vérification du rôle ADMIN
    # --------------------------------------------------------

    est_admin = (
        UtilisateurRole.objects
        .filter(
            utilisateur=utilisateur,
            role__code="ADMIN",
            role__actif=True,
            actif=True,
        )
        .exists()
    )


    if not est_admin:

        message_vers_notification(request, 'ERROR', "Vous n'avez pas accès au tableau de bord administrateur.", "Vous n'avez pas accès au tableau de bord administrateur.")

        return redirect("connexion")


    # --------------------------------------------------------
    # 4. Statistiques
    # --------------------------------------------------------

    nombre_eleves = (
        Eleve.objects
        .filter(actif=True)
        .count()
    )


    nombre_enseignants = (
        Enseignant.objects
        .filter(actif=True)
        .count()
    )


    nombre_utilisateurs = (
        Utilisateur.objects
        .filter(actif=True)
        .count()
    )


    nombre_classes = (
        Classe.objects
        .filter(actif=True)
        .count()
    )


    # --------------------------------------------------------
    # 5. Activités récentes
    # --------------------------------------------------------

    activites_recentes = (
        HistoriqueAction.objects
        .select_related(
            "utilisateur",
            "type_action",
        )
        .order_by("-date_action")[:10]
    )


    # --------------------------------------------------------
    # 6. Demandes d'autorisation
    # --------------------------------------------------------

    demandes_autorisation = (
        DemandeAutorisation.objects
        .filter(
            statut=DemandeAutorisation.EN_ATTENTE
        )
        .count()
    )


    # --------------------------------------------------------
    # 7. Anomalies critiques
    # --------------------------------------------------------

    anomalies_critiques = (
        Anomalie.objects
        .filter(
            gravite=Anomalie.CRITIQUE,
            statut__in=[
                Anomalie.OUVERTE,
                Anomalie.EN_COURS,
            ],
        )
        .count()
    )


    # --------------------------------------------------------
    # 8. Rôles de l'utilisateur
    # --------------------------------------------------------

    roles = (
        UtilisateurRole.objects
        .filter(
            utilisateur=utilisateur,
            actif=True,
            role__actif=True,
        )
        .select_related("role")
    )


    # --------------------------------------------------------
    # 9. Contexte
    # --------------------------------------------------------

    context = {
        "utilisateur": utilisateur,
        "roles": roles,
        "nombre_eleves": nombre_eleves,
        "nombre_enseignants": nombre_enseignants,
        "nombre_utilisateurs": nombre_utilisateurs,
        "nombre_classes": nombre_classes,
        "activites_recentes": activites_recentes,
        "demandes_autorisation": demandes_autorisation,
        "anomalies_critiques": anomalies_critiques,
    }

    # Le modele admin affiche aussi les compteurs d'inscriptions, de
    # paiements valides et le montant en caisse. La vue ne les fournissait
    # pas et le |default:"0" du template masquait le vide : les cartes
    # affichaient zero en permanence. Le contexte ecole les apporte.
    compteurs = _contexte_compteurs_ecole(request)
    if compteurs is not None:
        context.update(compteurs)


    # --------------------------------------------------------
    # 10. Affichage
    # --------------------------------------------------------

    return render(
        request,
        "admin/dashboard_admin.html",
        context,
    )


@permission_requise("utilisateur.consulter")
def liste_utilisateurs(request):
    """
    Affiche la liste des utilisateurs.

    L'accès est contrôlé par la permission :
        utilisateur.consulter
    """

    utilisateurs = (
        Utilisateur.objects
        .prefetch_related(
            "attributions_roles__role"
        )
        .order_by(
            "nom",
            "prenom"
        )
    )

    context = {
        "utilisateur": request.utilisateur,
        "utilisateurs": utilisateurs,
    }

    return render(
        request,
        "Gestion/liste_utilisateur.html",
        context,
    )
    
# ============================================================
# CRÉATION D'UN UTILISATEUR
# ============================================================

@permission_requise("utilisateur.creer")
def creer_utilisateur(request):

    utilisateur_id = request.session.get(
        "utilisateur_id"
    )

    if not utilisateur_id:
        return redirect("connexion")

    # --------------------------------------------------------
    # VÉRIFICATION ADMIN
    # --------------------------------------------------------

    est_admin = (
        UtilisateurRole.objects
        .filter(
            utilisateur_id=utilisateur_id,
            role__code="ADMIN",
            role__actif=True,
            actif=True,
        )
        .exists()
    )

    if not est_admin:

        message_vers_notification(request, 'ERROR', "Vous n'avez pas l'autorisation "
            "de créer un utilisateur.", "Vous n'avez pas l'autorisation "
            "de créer un utilisateur.")

        return redirect("connexion")

    # --------------------------------------------------------
    # RÉCUPÉRATION DES RÔLES
    # --------------------------------------------------------

    roles = (
        Role.objects
        .filter(actif=True)
        .order_by("libelle")
    )

    # ========================================================
    # TRAITEMENT POST
    # ========================================================

    if request.method == "POST":

        nom = request.POST.get(
            "nom",
            ""
        ).strip()

        postnom = request.POST.get(
            "postnom",
            ""
        ).strip()

        prenom = request.POST.get(
            "prenom",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        telephone = request.POST.get(
            "telephone",
            ""
        ).strip()

        login = request.POST.get(
            "login",
            ""
        ).strip()

        mot_de_passe = request.POST.get(
            "mot_de_passe",
            ""
        )

        role_id = request.POST.get(
            "role"
        )

        # ----------------------------------------------------
        # VÉRIFICATION DES CHAMPS OBLIGATOIRES
        # ----------------------------------------------------

        if (
            not nom
            or not prenom
            or not login
            or not mot_de_passe
        ):

            message_vers_notification(request, 'ERROR', "Veuillez remplir tous les champs obligatoires.", "Veuillez remplir tous les champs obligatoires.")

            return render(
                request,
                "Gestion/formulaire.html",
                {
                    "roles": roles,
                }
            )

        # ----------------------------------------------------
        # VÉRIFICATION DU LOGIN
        # ----------------------------------------------------

        if CompteUtilisateur.objects.filter(
            login=login
        ).exists():

            message_vers_notification(request, 'ERROR', "Ce login existe déjà.", "Ce login existe déjà.")

            return render(
                request,
                "Gestion/formulaire.html",
                {
                    "roles": roles,
                }
            )

        # ----------------------------------------------------
        # VÉRIFICATION DE L'EMAIL
        # ----------------------------------------------------

        if email and Utilisateur.objects.filter(
            email=email
        ).exists():

            message_vers_notification(request, 'ERROR', "Cette adresse email est déjà utilisée.", "Cette adresse email est déjà utilisée.")

            return render(
                request,
                "Gestion/formulaire.html",
                {
                    "roles": roles,
                }
            )

        # ====================================================
        # CRÉATION
        # ====================================================

        try:

            with transaction.atomic():

                # --------------------------------------------
                # 1. CRÉATION DE L'UTILISATEUR
                # --------------------------------------------

                utilisateur = Utilisateur.objects.create(

                    nom=nom,

                    postnom=postnom or None,

                    prenom=prenom,

                    email=email or None,

                    telephone=telephone or None,

                    actif=True,

                )

                # --------------------------------------------
                # 2. CRÉATION DU COMPTE
                # --------------------------------------------

                CompteUtilisateur.objects.create(

                    utilisateur=utilisateur,

                    login=login,

                    mot_de_passe_hash=make_password(
                        mot_de_passe
                    ),

                    changement_mdp_obligatoire=True,

                )

                # --------------------------------------------
                # 3. ATTRIBUTION DU RÔLE
                # --------------------------------------------

                role = None

                if role_id:

                    role = Role.objects.get(
                        id=role_id,
                        actif=True,
                    )

                    UtilisateurRole.objects.create(

                        utilisateur=utilisateur,

                        role=role,

                        actif=True,

                    )

                # --------------------------------------------
                # 4. ENREGISTREMENT DANS L'HISTORIQUE
                # --------------------------------------------

                nouvelle_valeur = (
                    f"Utilisateur créé : "
                    f"{utilisateur.prenom} "
                    f"{utilisateur.nom}"
                )

                if utilisateur.postnom:

                    nouvelle_valeur += (
                        f" {utilisateur.postnom}"
                    )

                nouvelle_valeur += (
                    f" | Login : {login}"
                )

                if role:

                    nouvelle_valeur += (
                        f" | Rôle : {role.libelle}"
                    )

                enregistrer_historique(

                    request=request,

                    code_action="UTILISATEUR_CREATION",

                    table_cible="utilisateur",

                    id_cible=utilisateur.id,

                    nouvelle_valeur=nouvelle_valeur,

                    motif=(
                        "Création d'un nouveau "
                        "compte utilisateur."
                    ),

                )

            # =================================================
            # SUCCÈS
            # =================================================

            message_vers_notification(request, 'SUCCESS', "L'utilisateur a été créé avec succès.", "L'utilisateur a été créé avec succès.")

            return redirect(
                "liste_utilisateurs"
            )

        # ====================================================
        # ERREUR : RÔLE
        # ====================================================

        except Role.DoesNotExist:

            message_vers_notification(request, 'ERROR', "Le rôle sélectionné n'existe pas.", "Le rôle sélectionné n'existe pas.")

        # ====================================================
        # AUTRES ERREURS
        # ====================================================

        except Exception as e:

            message_vers_notification(request, 'ERROR', f"Impossible de créer l'utilisateur : {e}", f"Impossible de créer l'utilisateur : {e}")

    # ========================================================
    # AFFICHAGE DU FORMULAIRE
    # ========================================================

    return render(
        request,
        "Gestion/formulaire.html",
        {
            "roles": roles,
        }
    )
    
# ============================================================
# MODIFICATION D'UN UTILISATEUR
# ============================================================

@permission_requise("utilisateur.modifier")
def modifier_utilisateur(request, utilisateur_id):
    """
    Modifie le profil, le compte et le rôle d'un utilisateur.

    Le mot de passe n'est volontairement PAS modifié ici.

    L'accès est contrôlé par la permission :
        utilisateur.modifier
    """

    # ========================================================
    # RÉCUPÉRATION DE L'UTILISATEUR
    # ========================================================

    utilisateur = get_object_or_404(
        Utilisateur,
        id=utilisateur_id
    )

    # ========================================================
    # COMPTE D'AUTHENTIFICATION
    # ========================================================

    compte = getattr(
        utilisateur,
        "compte",
        None
    )

    # ========================================================
    # RÔLE ACTUEL
    # ========================================================

    attribution_role = (
        UtilisateurRole.objects
        .filter(
            utilisateur=utilisateur,
            actif=True
        )
        .select_related(
            "role"
        )
        .first()
    )

    # ========================================================
    # RÔLES DISPONIBLES
    # ========================================================

    roles = (
        Role.objects
        .filter(
            actif=True
        )
        .order_by(
            "libelle"
        )
    )

    # ========================================================
    # TRAITEMENT DU FORMULAIRE
    # ========================================================

    if request.method == "POST":

        nom = request.POST.get(
            "nom",
            ""
        ).strip()

        postnom = request.POST.get(
            "postnom",
            ""
        ).strip()

        prenom = request.POST.get(
            "prenom",
            ""
        ).strip()

        telephone = request.POST.get(
            "telephone",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        login_compte = request.POST.get(
            "login",
            ""
        ).strip()

        role_id = request.POST.get(
            "role"
        )

        actif = (
            request.POST.get("actif") == "on"
        )

        # ====================================================
        # VALIDATIONS
        # ====================================================

        erreurs = []

        # ----------------------------------------------------
        # Nom
        # ----------------------------------------------------

        if not nom:

            erreurs.append(
                "Le nom est obligatoire."
            )

        # ----------------------------------------------------
        # Prénom
        # ----------------------------------------------------

        if not prenom:

            erreurs.append(
                "Le prénom est obligatoire."
            )

        # ----------------------------------------------------
        # Email
        # ----------------------------------------------------

        if not email:

            erreurs.append(
                "L'adresse email est obligatoire."
            )

        # ----------------------------------------------------
        # Login
        # ----------------------------------------------------

        if not login_compte:

            erreurs.append(
                "Le login est obligatoire."
            )

        # ====================================================
        # UNICITÉ DE L'EMAIL
        # ====================================================

        if email:

            email_existe = (
                Utilisateur.objects
                .filter(
                    email=email
                )
                .exclude(
                    id=utilisateur.id
                )
                .exists()
            )

            if email_existe:

                erreurs.append(
                    "Cette adresse email est déjà utilisée."
                )

        # ====================================================
        # UNICITÉ DU LOGIN
        # ====================================================

        if compte:

            login_existe = (
                CompteUtilisateur.objects
                .filter(
                    login=login_compte
                )
                .exclude(
                    id=compte.id
                )
                .exists()
            )

            if login_existe:

                erreurs.append(
                    "Ce login est déjà utilisé."
                )

        # ====================================================
        # RÔLE
        # ====================================================

        role = None

        if role_id:

            role = get_object_or_404(
                Role,
                id=role_id,
                actif=True
            )

        else:

            erreurs.append(
                "Veuillez sélectionner un rôle."
            )

        # ====================================================
        # AFFICHAGE DES ERREURS
        # ====================================================

        if erreurs:

            for erreur in erreurs:

                message_vers_notification(request, 'ERROR', erreur, erreur)

            return render(
                request,
                "Gestion/modifier_utilisateur.html",
                {
                    "utilisateur": utilisateur,
                    "compte": compte,
                    "roles": roles,
                    "attribution_role": attribution_role,
                }
            )
        #=====================================================
        #HISTORIQUE
        #=====================================================
        ancienne_valeur = (
            f"Nom : {utilisateur.nom}"
            f" | Postnom : {utilisateur.postnom or 'Non renseigné'}"
            f" | Prénom : {utilisateur.prenom}"
            f" | Téléphone : {utilisateur.telephone or 'Non renseigné'}"
            f" | Email : {utilisateur.email or 'Non renseigné'}"
            f" | Actif : {'Oui' if utilisateur.actif else 'Non'}"
        )

        if compte:
            ancienne_valeur += (
                f" | Login : {compte.login}"
            )

        if attribution_role:
            ancienne_valeur += (
                f" | Rôle : {attribution_role.role.libelle}"
            )

        # ====================================================
        # ENREGISTREMENT
        # ====================================================

        with transaction.atomic():

            # ------------------------------------------------
            # 1. Modification du profil
            # ------------------------------------------------

            utilisateur.nom = nom

            utilisateur.postnom = (
                postnom or None
            )

            utilisateur.prenom = prenom

            utilisateur.telephone = (
                telephone or None
            )

            utilisateur.email = (
                email or None
            )

            utilisateur.actif = actif

            utilisateur.save()

            # ------------------------------------------------
            # 2. Modification du compte
            # ------------------------------------------------

            if compte:

                compte.login = login_compte

                compte.save()

            # ------------------------------------------------
            # 3. Modification du rôle
            # ------------------------------------------------

            if role:

                # Désactivation des anciennes
                # attributions actives.

                UtilisateurRole.objects.filter(
                    utilisateur=utilisateur,
                    actif=True
                ).update(
                    actif=False
                )

                # Recherche d'une ancienne attribution
                # pour le même rôle.

                attribution = (
                    UtilisateurRole.objects
                    .filter(
                        utilisateur=utilisateur,
                        role=role
                    )
                    .first()
                )

                if attribution:

                    attribution.actif = True

                    attribution.save(
                        update_fields=[
                            "actif"
                        ]
                    )

                else:

                    UtilisateurRole.objects.create(
                        utilisateur=utilisateur,
                        role=role,
                        actif=True
                    )
# -------------------------------------------------
# 4. ENREGISTREMENT DE L'HISTORIQUE
# -------------------------------------------------

        nouvelle_valeur = (
            f"Nom : {utilisateur.nom}"
            f" | Postnom : {utilisateur.postnom or 'Non renseigné'}"
            f" | Prénom : {utilisateur.prenom}"
            f" | Téléphone : {utilisateur.telephone or 'Non renseigné'}"
            f" | Email : {utilisateur.email or 'Non renseigné'}"
            f" | Actif : {'Oui' if utilisateur.actif else 'Non'}"
        )

        if compte:
            nouvelle_valeur += (
                f" | Login : {compte.login}"
            )

        if role:
            nouvelle_valeur += (
                f" | Rôle : {role.libelle}"
            )

        enregistrer_historique(
            request=request,
            code_action="UTILISATEUR_MODIFICATION",
            table_cible="utilisateur",
            id_cible=utilisateur.id,
            ancienne_valeur=ancienne_valeur,
            nouvelle_valeur=nouvelle_valeur,
            motif="Modification des informations de l'utilisateur.",
        )
        # ====================================================
        # SUCCÈS
        # ====================================================

        message_vers_notification(request, 'SUCCESS', "L'utilisateur a été modifié avec succès.", "L'utilisateur a été modifié avec succès.")

        return redirect(
            "liste_utilisateurs"
        )

    # ========================================================
    # AFFICHAGE INITIAL
    # ========================================================

    return render(
        request,
        "Gestion/modifier_utilisateur.html",
        {
            "utilisateur": utilisateur,
            "compte": compte,
            "roles": roles,
            "attribution_role": attribution_role,
        }
    )

def changer_mot_de_passe(request):
    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return redirect("connexion")

    try:
        compte = CompteUtilisateur.objects.get(
            utilisateur_id=utilisateur_id
        )
    except CompteUtilisateur.DoesNotExist:
        request.session.flush()
        message_vers_notification(request, 'ERROR', "Compte utilisateur introuvable.", "Compte utilisateur introuvable.")
        return redirect("connexion")

    # URL du tableau de bord de l'utilisateur (le nom de route depend du role)
    nom_route = nom_tableau_de_bord(request.session.get("roles"))
    CONTEXTE_CHANGER_MDP = {
        "utilisateur": compte.utilisateur,
        "tableau_de_bord_url": reverse(nom_route) if nom_route else reverse("connexion"),
    }

    if request.method == "POST":
        ancien_mot_de_passe = request.POST.get(
            "ancien_mot_de_passe",
            ""
        )

        nouveau_mot_de_passe = request.POST.get(
            "nouveau_mot_de_passe",
            ""
        )

        confirmation = request.POST.get(
            "confirmation",
            ""
        )

        # Vérification de l'ancien mot de passe
        from django.contrib.auth.hashers import check_password

        if not check_password(
            ancien_mot_de_passe,
            compte.mot_de_passe_hash
        ):
            message_vers_notification(request, 'ERROR', "L'ancien mot de passe est incorrect.", "L'ancien mot de passe est incorrect.")
            return render(
                request,
                "Gestion/authentification/changer_mot_de_passe.html",
                CONTEXTE_CHANGER_MDP
            )

        # Vérification de la longueur
        if len(nouveau_mot_de_passe) < 8:
            message_vers_notification(request, 'ERROR', "Le nouveau mot de passe doit contenir "
                "au moins 8 caractères.", "Le nouveau mot de passe doit contenir "
                "au moins 8 caractères.")
            return render(
                request,
                "Gestion/authentification/changer_mot_de_passe.html",
                CONTEXTE_CHANGER_MDP
            )

        # Confirmation
        if nouveau_mot_de_passe != confirmation:
            message_vers_notification(request, 'ERROR', "Les deux nouveaux mots de passe ne correspondent pas.", "Les deux nouveaux mots de passe ne correspondent pas.")
            return render(
                request,
                "Gestion/authentification/changer_mot_de_passe.html",
                CONTEXTE_CHANGER_MDP
            )

        # Empêcher de reprendre exactement l'ancien
        if check_password(
            nouveau_mot_de_passe,
            compte.mot_de_passe_hash
        ):
            message_vers_notification(request, 'ERROR', "Le nouveau mot de passe doit être différent "
                "de l'ancien.", "Le nouveau mot de passe doit être différent "
                "de l'ancien.")
            return render(
                request,
                "Gestion/authentification/changer_mot_de_passe.html",
                CONTEXTE_CHANGER_MDP
            )

        # Nouveau hash
        compte.mot_de_passe_hash = make_password(
            nouveau_mot_de_passe
        )

        compte.changement_mdp_obligatoire = False

        compte.save(
            update_fields=[
                "mot_de_passe_hash",
                "changement_mdp_obligatoire",
            ]
        )

        message_vers_notification(request, 'SUCCESS', "Votre mot de passe a été modifié avec succès.", "Votre mot de passe a été modifié avec succès.")

        nom_route = nom_tableau_de_bord(request.session.get("roles"))
        if nom_route:
            return redirect(nom_route)
        return redirect("connexion")

    return render(
        request,
        "Gestion/authentification/changer_mot_de_passe.html",
        CONTEXTE_CHANGER_MDP
    )
    

# ============================================================
# DÉSACTIVATION D'UN UTILISATEUR
# ============================================================

@permission_requise("utilisateur.desactiver")
def desactiver_utilisateur(request, utilisateur_id):
    """
    Active ou désactive un utilisateur.
    Le même bouton permet de changer l'état :
    actif -> désactivé
    désactivé -> actif
    """

    if request.method != "POST":
        return redirect(
            "detail_utilisateur",
            utilisateur_id=utilisateur_id
        )

    utilisateur = get_object_or_404(
        Utilisateur,
        id=utilisateur_id
    )

    with transaction.atomic():

        # -------------------------------------------------
        # DÉSACTIVATION
        # -------------------------------------------------

        if utilisateur.actif:

            ancienne_valeur = "Statut : Actif"

            utilisateur.actif = False

            utilisateur.save(
                update_fields=["actif"]
            )

            enregistrer_historique(
                request=request,
                code_action="UTILISATEUR_DESACTIVATION",
                table_cible="utilisateur",
                id_cible=utilisateur.id,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur="Statut : Désactivé",
                motif="Désactivation du compte utilisateur.",
            )

            message_vers_notification(request, 'SUCCESS', f"L'utilisateur {utilisateur.prenom} "
                f"{utilisateur.nom} a été désactivé.", f"L'utilisateur {utilisateur.prenom} "
                f"{utilisateur.nom} a été désactivé.")

        # -------------------------------------------------
        # ACTIVATION
        # -------------------------------------------------

        else:

            ancienne_valeur = "Statut : Désactivé"

            utilisateur.actif = True

            utilisateur.save(
                update_fields=["actif"]
            )

            enregistrer_historique(
                request=request,
                code_action="UTILISATEUR_ACTIVATION",
                table_cible="utilisateur",
                id_cible=utilisateur.id,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur="Statut : Actif",
                motif="Activation du compte utilisateur.",
            )

            message_vers_notification(request, 'SUCCESS', f"L'utilisateur {utilisateur.prenom} "
                f"{utilisateur.nom} a été activé.", f"L'utilisateur {utilisateur.prenom} "
                f"{utilisateur.nom} a été activé.")

    return redirect(
        "detail_utilisateur",
        utilisateur_id=utilisateur.id
    )

# ============================================================
# DÉTAIL D'UN UTILISATEUR
# ============================================================

@permission_requise("utilisateur.consulter")
def detail_utilisateur(request, utilisateur_id):
    """
    Affiche les informations détaillées,
    l'état actuel et l'activité récente
    concernant un utilisateur.
    """

    # --------------------------------------------------------
    # UTILISATEUR
    # --------------------------------------------------------
    utilisateur = get_object_or_404(
        Utilisateur,
        id=utilisateur_id
    )

    # --------------------------------------------------------
    # COMPTE D'AUTHENTIFICATION
    # --------------------------------------------------------
    compte = (
        CompteUtilisateur.objects
        .filter(
            utilisateur=utilisateur
        )
        .first()
    )

    # --------------------------------------------------------
    # RÔLES ACTIFS
    # --------------------------------------------------------
    roles = (
        UtilisateurRole.objects
        .filter(
            utilisateur=utilisateur,
            actif=True,
            role__actif=True,
        )
        .select_related("role")
        .order_by("-date_attribution")
    )

    # --------------------------------------------------------
    # ACTIVITÉ RÉCENTE
    #
    # Les historiques concernant cet utilisateur sont
    # identifiés par :
    # table_cible = "utilisateur"
    # id_cible = ID de l'utilisateur affiché
    # --------------------------------------------------------
    historiques = (
        HistoriqueAction.objects
        .filter(
            table_cible="utilisateur",
            id_cible=utilisateur.id,
        )
        .select_related(
            "utilisateur",
            "type_action",
        )
        .order_by("-date_action")[:10]
    )

    context = {
        "utilisateur": utilisateur,
        "compte": compte,
        "roles": roles,
        "historiques": historiques,
    }

    return render(
        request,
        "Gestion/detail_utilisateur.html",
        context,
    )

@permission_requise("utilisateur.modifier")
def reinitialiser_mot_de_passe(
    request,
    utilisateur_id
):

    utilisateur = get_object_or_404(
        Utilisateur,
        id=utilisateur_id
    )

    compte = get_object_or_404(
        CompteUtilisateur,
        utilisateur=utilisateur
    )

    if request.method == "POST":

        nouveau_mot_de_passe = request.POST.get(
            "mot_de_passe",
            ""
        )

        confirmation_mot_de_passe = request.POST.get(
            "confirmation_mot_de_passe",
            ""
        )

        if not nouveau_mot_de_passe:
            message_vers_notification(request, 'ERROR', "Veuillez saisir le nouveau mot de passe.", "Veuillez saisir le nouveau mot de passe.")

        elif (
            nouveau_mot_de_passe
            != confirmation_mot_de_passe
        ):
            message_vers_notification(request, 'ERROR', "Les mots de passe ne correspondent pas.", "Les mots de passe ne correspondent pas.")

        else:

            with transaction.atomic():

                compte.mot_de_passe_hash = make_password(
                    nouveau_mot_de_passe
                )

                compte.changement_mdp_obligatoire = True

                compte.echecs_connexion = 0

                compte.verrouille_jusqu_a = None

                compte.save(
                    update_fields=[
                        "mot_de_passe_hash",
                        "changement_mdp_obligatoire",
                        "echecs_connexion",
                        "verrouille_jusqu_a",
                    ]
                )

                # -----------------------------------------
                # HISTORIQUE
                # -----------------------------------------

                enregistrer_historique(
                    request=request,
                    code_action=(
                        "UTILISATEUR_REINITIALISATION_MDP"
                    ),
                    table_cible="compte_utilisateur",
                    id_cible=compte.id,
                    nouvelle_valeur=(
                        "Mot de passe réinitialisé. "
                        "Le changement du mot de passe est "
                        "obligatoire à la prochaine connexion."
                    ),
                    motif=(
                        "Réinitialisation administrative "
                        "du mot de passe."
                    ),
                )

            message_vers_notification(request, 'SUCCESS', "Le mot de passe a été réinitialisé avec succès.", "Le mot de passe a été réinitialisé avec succès.")

            return redirect(
                "detail_utilisateur",
                utilisateur_id=utilisateur.id
            )

    return render(
        request,
        "Gestion/reinitialiser_mot_de_passe.html",
        {
            "utilisateur": utilisateur,
            "compte": compte,
        }
    )
    
@permission_requise("utilisateur.consulter")
def activites_utilisateur(request, utilisateur_id):
    """
    Affiche l'historique des activités
    concernant un utilisateur.
    """

    # --------------------------------------------------------
    # UTILISATEUR CONCERNÉ
    # --------------------------------------------------------
    utilisateur = get_object_or_404(
        Utilisateur,
        id=utilisateur_id
    )

    # --------------------------------------------------------
    # HISTORIQUE DES ACTIVITÉS
    # --------------------------------------------------------
    activites = (
        HistoriqueAction.objects
        .filter(
            table_cible="utilisateur",
            id_cible=utilisateur.id
        )
        .select_related(
            "utilisateur",
            "type_action"
        )
        .order_by("-date_action")
    )

    context = {
        "utilisateur": utilisateur,
        "activites": activites,
    }

    return render(
        request,
        "Gestion/activites_utilisateur.html",
        context,
    )

@permission_requise("annee.consulter")
def liste_annees(request):
    """
    Affiche la liste des années scolaires
    et identifie l'année actuellement active.
    """

    # --------------------------------------------------------
    # Liste des années scolaires
    # --------------------------------------------------------

    annees = AnneeScolaire.objects.all()

    # --------------------------------------------------------
    # Année actuellement active
    # --------------------------------------------------------

    annee_active = (
        AnneeScolaire.objects
        .filter(
            statut=AnneeScolaire.ACTIVE
        )
        .first()
    )

    # --------------------------------------------------------
    # Contexte
    # --------------------------------------------------------

    context = {
        "annees": annees,
        "annee_active": annee_active,
    }

    return render(
        request,
        "annee/liste_annees.html",
        context,
    )

@permission_requise("annee.creer")
def creer_annee(request):
    """
    Permet de créer une nouvelle année scolaire.
    """

    if request.method == "POST":

        libelle = request.POST.get(
            "libelle",
            ""
        ).strip()

        date_debut = request.POST.get(
            "date_debut",
            ""
        )

        date_fin = request.POST.get(
            "date_fin",
            ""
        )

        seuil_passage = request.POST.get(
            "seuil_passage",
            "50"
        )

        statut = request.POST.get(
            "statut",
            AnneeScolaire.PLANIFIEE
        )

        # ----------------------------------------------------
        # Vérification des champs obligatoires
        # ----------------------------------------------------

        if not libelle or not date_debut or not date_fin:

            message_vers_notification(request, 'ERROR', "Veuillez remplir tous les champs obligatoires.", "Veuillez remplir tous les champs obligatoires.")

            return render(
                request,
                "annee/creer_annee.html"
            )

        # ----------------------------------------------------
        # Vérification du statut
        # ----------------------------------------------------

        statuts_valides = [
            AnneeScolaire.PLANIFIEE,
            AnneeScolaire.ACTIVE,
        ]

        if statut not in statuts_valides:

            message_vers_notification(request, 'ERROR', "Le statut sélectionné est invalide.", "Le statut sélectionné est invalide.")

            return render(
                request,
                "annee/creer_annee.html"
            )

        # ----------------------------------------------------
        # Une seule année active
        # ----------------------------------------------------

        if statut == AnneeScolaire.ACTIVE:

            annee_active = (
                AnneeScolaire.objects
                .filter(
                    statut=AnneeScolaire.ACTIVE
                )
                .exists()
            )

            if annee_active:

                message_vers_notification(request, 'ERROR', "Une année scolaire est déjà active. "
                    "Vous devez d'abord la clôturer avant "
                    "d'activer une nouvelle année.", "Une année scolaire est déjà active. "
                    "Vous devez d'abord la clôturer avant "
                    "d'activer une nouvelle année.")

                return render(
                    request,
                    "annee/creer_annee.html"
                )

        # ----------------------------------------------------
        # Création
        # ----------------------------------------------------

        try:

            with transaction.atomic():

                annee = AnneeScolaire(
                    libelle=libelle,
                    date_debut=date_debut,
                    date_fin=date_fin,
                    seuil_passage=seuil_passage,
                    statut=statut,
                )

                # Exécute les validations du modèle
                annee.full_clean()

                annee.save()

            message_vers_notification(request, 'SUCCESS', f"L'année scolaire {annee.libelle} "
                f"a été créée avec succès.", f"L'année scolaire {annee.libelle} "
                f"a été créée avec succès.")

            return redirect(
                "liste_annees"
            )

        except Exception as erreur:

            message_vers_notification(request, 'ERROR', f"Impossible de créer l'année scolaire : "
                f"{erreur}", f"Impossible de créer l'année scolaire : "
                f"{erreur}")

    return render(
        request,
        "annee/creer_annee.html"
    )

@permission_requise("annee.consulter")
def detail_annee(request, annee_id):
    """
    Affiche les informations détaillées
    d'une année scolaire.
    """

    annee = get_object_or_404(
        AnneeScolaire,
        id=annee_id
    )

    context = {
        "annee": annee,
    }

    return render(
        request,
        "annee/detail_annee.html",
        context,
    )

@permission_requise("annee.modifier")
def modifier_annee(request, annee_id):
    """
    Permet de modifier les informations
    d'une année scolaire non clôturée.
    """

    annee = get_object_or_404(
        AnneeScolaire,
        id=annee_id
    )

    # --------------------------------------------------------
    # Une année clôturée ne peut plus être modifiée
    # --------------------------------------------------------
    if annee.statut == AnneeScolaire.CLOTUREE:

        message_vers_notification(request, 'ERROR', "Une année scolaire clôturée ne peut plus être modifiée.", "Une année scolaire clôturée ne peut plus être modifiée.")

        return redirect(
            "detail_annee",
            annee_id=annee.id
        )

    # --------------------------------------------------------
    # TRAITEMENT DU FORMULAIRE
    # --------------------------------------------------------
    if request.method == "POST":

        form = AnneeScolaireForm(
            request.POST,
            instance=annee
        )

        if form.is_valid():

            annee_modifiee = form.save()

            message_vers_notification(request, 'SUCCESS', f"L'année scolaire "
                f"« {annee_modifiee.libelle} » "
                f"a été modifiée avec succès.", f"L'année scolaire "
                f"« {annee_modifiee.libelle} » "
                f"a été modifiée avec succès.")

            return redirect(
                "detail_annee",
                annee_id=annee_modifiee.id
            )

    else:

        form = AnneeScolaireForm(
            instance=annee
        )

    context = {
        "annee": annee,
        "form": form,
    }

    return render(
        request,
        "annee/modifier_annee.html",
        context,
    )
    
@permission_requise("annee.activer")
def activer_annee(request, annee_id):

    annee = get_object_or_404(
        AnneeScolaire,
        id=annee_id
    )

    # Une année clôturée ne peut plus être activée
    if annee.statut == AnneeScolaire.CLOTUREE:

        message_vers_notification(request, 'ERROR', "Une année scolaire clôturée ne peut plus être activée.", "Une année scolaire clôturée ne peut plus être activée.")

        return redirect(
            "detail_annee",
            annee_id=annee.id
        )

    # Une autre année est-elle déjà active ?
    annee_active = (
        AnneeScolaire.objects
        .filter(
            statut=AnneeScolaire.ACTIVE
        )
        .exclude(
            id=annee.id
        )
        .first()
    )

    if annee_active:

        message_vers_notification(request, 'ERROR', f"L'année scolaire « {annee_active.libelle} » "
            f"est actuellement active. "
            f"Elle doit d'abord être clôturée avant "
            f"d'activer une nouvelle année.", f"L'année scolaire « {annee_active.libelle} » "
            f"est actuellement active. "
            f"Elle doit d'abord être clôturée avant "
            f"d'activer une nouvelle année.")

        return redirect(
            "detail_annee",
            annee_id=annee.id
        )

    # Affichage de la page de confirmation
    if request.method != "POST":

        return render(
            request,
            "annee/activer_annee.html",
            {
                "annee": annee,
            }
        )

    # Activation
    with transaction.atomic():

        annee.statut = AnneeScolaire.ACTIVE

        annee.save(
            update_fields=["statut"]
        )

    message_vers_notification(request, 'SUCCESS', f"L'année scolaire « {annee.libelle} » "
        f"a été activée avec succès.", f"L'année scolaire « {annee.libelle} » "
        f"a été activée avec succès.")

    return redirect(
        "detail_annee",
        annee_id=annee.id
    )

@permission_requise("annee.cloturer")
def cloturer_annee(request, annee_id):
    """
    Affiche l'état des conditions nécessaires
    à la clôture d'une année scolaire.

    La clôture définitive sera automatisée lorsque
    le module des proclamations et les contrôles
    pédagogiques seront complètement intégrés.
    """

    annee = get_object_or_404(
        AnneeScolaire,
        id=annee_id
    )

    # --------------------------------------------------------
    # DATE DE FIN
    # --------------------------------------------------------

    aujourd_hui = timezone.localdate()

    date_fin_atteinte = (
        aujourd_hui >= annee.date_fin
    )

    # --------------------------------------------------------
    # CONDITIONS FUTURES
    #
    # Ces contrôles seront reliés aux modèles réels
    # lorsque les modules correspondants seront terminés.
    # --------------------------------------------------------

    proclamation_terminee = False

    resultats_finalises = False

    operations_terminees = False

    # --------------------------------------------------------
    # CLÔTURE POSSIBLE
    # --------------------------------------------------------

    cloture_possible = (
        date_fin_atteinte
        and proclamation_terminee
        and resultats_finalises
        and operations_terminees
    )

    context = {
        "annee": annee,
        "date_fin_atteinte": date_fin_atteinte,
        "proclamation_terminee": proclamation_terminee,
        "resultats_finalises": resultats_finalises,
        "operations_terminees": operations_terminees,
        "cloture_possible": cloture_possible,
    }

    return render(
        request,
        "annee/cloturer_annee.html",
        context,
    )

@permission_requise("annee.consulter")
def structure_academique(request):

    # --------------------------------------------------------
    # ANNÉE SCOLAIRE ACTIVE
    # --------------------------------------------------------
    annee_active = (
        AnneeScolaire.objects
        .filter(
            statut=AnneeScolaire.ACTIVE
        )
        .first()
    )

    # --------------------------------------------------------
    # NOMBRE D'ANNÉES SCOLAIRES
    # --------------------------------------------------------
    nombre_annees = (
        AnneeScolaire.objects
        .count()
    )

    # --------------------------------------------------------
    # NOMBRE DE SECTIONS ACTIVES
    # --------------------------------------------------------
    nombre_sections = (
        Section.objects
        .filter(
            actif=True
        )
        .count()
    )

    # --------------------------------------------------------
    # NOMBRE DE NIVEAUX ACTIFS
    # --------------------------------------------------------
    nombre_niveaux = (
        Niveau.objects
        .filter(
            actif=True
        )
        .count()
    )

    # --------------------------------------------------------
    # NOMBRE DE CLASSES
    #
    # Si une année est active, on compte uniquement les
    # classes de cette année.
    # --------------------------------------------------------
    if annee_active:

        nombre_classes = (
            Classe.objects
            .filter(
                annee=annee_active,
                actif=True,
            )
            .count()
        )

    else:

        nombre_classes = 0

    # --------------------------------------------------------
    # NOMBRE DE MATIÈRES ACTIVES
    # --------------------------------------------------------
    nombre_matieres = (
        Matiere.objects
        .filter(
            actif=True
        )
        .count()
    )

    # --------------------------------------------------------
    # CONTEXTE
    # --------------------------------------------------------
    context = {
        "annee_active": annee_active,
        "nombre_annees": nombre_annees,
        "nombre_sections": nombre_sections,
        "nombre_niveaux": nombre_niveaux,
        "nombre_classes": nombre_classes,
        "nombre_matieres": nombre_matieres,
    }

    return render(
        request,
        "annee/structure_academique.html",
        context,
    )

@permission_requise("section.consulter")
def liste_sections(request):

    # --------------------------------------------------------
    # RÉCUPÉRATION DE LA RECHERCHE
    # --------------------------------------------------------
    recherche = request.GET.get(
        "q",
        ""
    ).strip()

    # --------------------------------------------------------
    # LISTE DES SECTIONS
    # --------------------------------------------------------
    sections = (
        Section.objects
        .all()
    )

    # --------------------------------------------------------
    # RECHERCHE PAR CODE OU LIBELLÉ
    # --------------------------------------------------------
    if recherche:

        sections = sections.filter(
            Q(
                code__icontains=recherche
            )
            |
            Q(
                libelle__icontains=recherche
            )
        )

    # --------------------------------------------------------
    # CONTEXTE
    # --------------------------------------------------------
    context = {
        "sections": sections,
        "recherche": recherche,
    }

    return render(
        request,
        "annee/liste_sections.html",
        context,
    )

@permission_requise("section.creer")
def creer_section(request):

    # --------------------------------------------------------
    # DONNÉES PAR DÉFAUT
    # --------------------------------------------------------
    donnees = {
        "code": "",
        "libelle": "",
        "actif": True,
    }

    erreurs = {}

    # --------------------------------------------------------
    # TRAITEMENT DU FORMULAIRE
    # --------------------------------------------------------
    if request.method == "POST":

        code = request.POST.get(
            "code",
            ""
        ).strip().upper()

        libelle = request.POST.get(
            "libelle",
            ""
        ).strip()

        actif = (
            request.POST.get("actif")
            == "on"
        )

        # ----------------------------------------------------
        # CONSERVATION DES DONNÉES EN CAS D'ERREUR
        # ----------------------------------------------------
        donnees = {
            "code": code,
            "libelle": libelle,
            "actif": actif,
        }

        # ----------------------------------------------------
        # VALIDATION DU CODE
        # ----------------------------------------------------
        if not code:

            erreurs["code"] = (
                "Le code de la section est obligatoire."
            )

        elif Section.objects.filter(
            code__iexact=code
        ).exists():

            erreurs["code"] = (
                "Une section utilise déjà ce code."
            )

        # ----------------------------------------------------
        # VALIDATION DU LIBELLÉ
        # ----------------------------------------------------
        if not libelle:

            erreurs["libelle"] = (
                "Le libellé de la section est obligatoire."
            )

        elif Section.objects.filter(
            libelle__iexact=libelle
        ).exists():

            erreurs["libelle"] = (
                "Une section utilise déjà ce libellé."
            )

        # ----------------------------------------------------
        # ENREGISTREMENT
        # ----------------------------------------------------
        if not erreurs:

            section = Section.objects.create(
                code=code,
                libelle=libelle,
                actif=actif,
            )

            message_vers_notification(request, 'SUCCESS', f"La section « {section.libelle} » "
                "a été créée avec succès.", f"La section « {section.libelle} » "
                "a été créée avec succès.")

            return redirect(
                "liste_sections"
            )

    # --------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------
    context = {
        "donnees": donnees,
        "erreurs": erreurs,
    }

    return render(
        request,
        "annee/creer_section.html",
        context,
    )

@permission_requise("section.consulter")
def detail_section(request, section_id):
    """
    Affiche les informations détaillées d'une section
    ainsi que les classes qui lui sont associées.
    """

    # --------------------------------------------------------
    # RÉCUPÉRATION DE LA SECTION
    # --------------------------------------------------------

    section = get_object_or_404(
        Section,
        id=section_id
    )

    # --------------------------------------------------------
    # CLASSES ASSOCIÉES À LA SECTION
    # --------------------------------------------------------

    classes = (
        Classe.objects
        .filter(
            section=section
        )
        .select_related(
            "annee",
            "niveau",
        )
        .order_by(
            "-annee__date_debut",
            "niveau__ordre",
            "code",
        )
    )

    # --------------------------------------------------------
    # STATISTIQUES
    # --------------------------------------------------------

    nombre_classes = classes.count()

    nombre_classes_actives = (
        classes
        .filter(
            actif=True
        )
        .count()
    )

    # --------------------------------------------------------
    # CONTEXTE
    # --------------------------------------------------------

    context = {
        "section": section,
        "classes": classes,
        "nombre_classes": nombre_classes,
        "nombre_classes_actives": nombre_classes_actives,
    }

    return render(
        request,
        "annee/detail_section.html",
        context,
    )

@permission_requise("section.modifier")
def modifier_section(request, section_id):
    """
    Permet de modifier les informations
    d'une section existante.
    """

    # --------------------------------------------------------
    # RÉCUPÉRATION DE LA SECTION
    # --------------------------------------------------------

    section = get_object_or_404(
        Section,
        id=section_id
    )

    # --------------------------------------------------------
    # VALEURS PAR DÉFAUT
    # --------------------------------------------------------

    donnees = {
        "code": section.code,
        "libelle": section.libelle,
    }

    erreurs = {}

    # --------------------------------------------------------
    # TRAITEMENT DU FORMULAIRE
    # --------------------------------------------------------

    if request.method == "POST":

        code = request.POST.get(
            "code",
            ""
        ).strip()

        libelle = request.POST.get(
            "libelle",
            ""
        ).strip()

        # ----------------------------------------------------
        # VALIDATION DU CODE
        # ----------------------------------------------------

        if not code:
            erreurs["code"] = (
                "Le code de la section est obligatoire."
            )

        elif Section.objects.filter(
            code=code
        ).exclude(
            id=section.id
        ).exists():

            erreurs["code"] = (
                "Une autre section utilise déjà ce code."
            )

        # ----------------------------------------------------
        # VALIDATION DU LIBELLÉ
        # ----------------------------------------------------

        if not libelle:
            erreurs["libelle"] = (
                "Le libellé de la section est obligatoire."
            )

        # ----------------------------------------------------
        # CONSERVATION DES DONNÉES SAISIES
        # ----------------------------------------------------

        donnees = {
            "code": code,
            "libelle": libelle,
        }

        # ----------------------------------------------------
        # ENREGISTREMENT
        # ----------------------------------------------------

        if not erreurs:

            section.code = code
            section.libelle = libelle

            section.save(
                update_fields=[
                    "code",
                    "libelle",
                ]
            )

            message_vers_notification(request, 'SUCCESS', "La section a été modifiée avec succès.", "La section a été modifiée avec succès.")

            return redirect(
                "detail_section",
                section_id=section.id
            )

    # --------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------

    context = {
        "section": section,
        "donnees": donnees,
        "erreurs": erreurs,
    }

    return render(
        request,
        "annee/modifier_section.html",
        context,
    )

@permission_requise("section.desactiver")
def activer_desactiver_section(request, section_id):
    """
    Active ou désactive une section.

    Une section ne peut pas être désactivée
    lorsqu'elle possède encore des classes actives.
    """

    # --------------------------------------------------------
    # RÉCUPÉRATION DE LA SECTION
    # --------------------------------------------------------

    section = get_object_or_404(
        Section,
        id=section_id
    )

    # --------------------------------------------------------
    # SÉCURITÉ
    # --------------------------------------------------------

    if request.method != "POST":
        return redirect(
            "detail_section",
            section_id=section.id
        )

    # --------------------------------------------------------
    # DÉSACTIVATION
    # --------------------------------------------------------

    if section.actif:

        classes_actives = Classe.objects.filter(
            section=section,
            actif=True
        ).exists()

        if classes_actives:

            message_vers_notification(request, 'ERROR', "Impossible de désactiver cette section, "
                "car elle possède encore une ou plusieurs "
                "classes actives.", "Impossible de désactiver cette section, "
                "car elle possède encore une ou plusieurs "
                "classes actives.")

            return redirect(
                "detail_section",
                section_id=section.id
            )

        section.actif = False
        section.save(
            update_fields=["actif"]
        )

        message_vers_notification(request, 'SUCCESS', "La section a été désactivée avec succès.", "La section a été désactivée avec succès.")

    # --------------------------------------------------------
    # ACTIVATION
    # --------------------------------------------------------

    else:

        section.actif = True
        section.save(
            update_fields=["actif"]
        )

        message_vers_notification(request, 'SUCCESS', "La section a été activée avec succès.", "La section a été activée avec succès.")

    # --------------------------------------------------------
    # REDIRECTION
    # --------------------------------------------------------

    return redirect(
        "detail_section",
        section_id=section.id
    )

@permission_requise("niveau.consulter")
def liste_niveaux(request):
    """
    Affiche la liste des niveaux
    de la structure académique.
    """

    # --------------------------------------------------------
    # RÉCUPÉRATION DES NIVEAUX
    # --------------------------------------------------------

    niveaux = Niveau.objects.all().order_by(
        "ordre"
    )

    # --------------------------------------------------------
    # STATISTIQUES
    # --------------------------------------------------------

    nombre_niveaux = niveaux.count()

    nombre_niveaux_actifs = (
        niveaux
        .filter(actif=True)
        .count()
    )

    nombre_niveaux_inactifs = (
        niveaux
        .filter(actif=False)
        .count()
    )

    # --------------------------------------------------------
    # CONTEXTE
    # --------------------------------------------------------

    context = {
        "niveaux": niveaux,
        "nombre_niveaux": nombre_niveaux,
        "nombre_niveaux_actifs": nombre_niveaux_actifs,
        "nombre_niveaux_inactifs": nombre_niveaux_inactifs,
    }

    return render(
        request,
        "annee/liste_niveau.html",
        context,
    )

@permission_requise("niveau.creer")
def creer_niveau(request):
    """
    Permet de créer un nouveau niveau
    dans la structure académique.
    """

    # --------------------------------------------------------
    # TRAITEMENT DU FORMULAIRE
    # --------------------------------------------------------

    if request.method == "POST":

        form = NiveauForm(
            request.POST
        )

        if form.is_valid():

            niveau = form.save()

            message_vers_notification(request, 'SUCCESS', f"Le niveau « {niveau.libelle} » "
                "a été créé avec succès.", f"Le niveau « {niveau.libelle} » "
                "a été créé avec succès.")

            return redirect(
                "detail_niveau",
                niveau_id=niveau.id
            )

    # --------------------------------------------------------
    # AFFICHAGE DU FORMULAIRE
    # --------------------------------------------------------

    else:

        form = NiveauForm()

    # --------------------------------------------------------
    # CONTEXTE
    # --------------------------------------------------------

    context = {
        "form": form,
    }

    return render(
        request,
        "annee/creer_niveau.html",
        context,
    )

@permission_requise("niveau.consulter")
def detail_niveau(request, niveau_id):
    """
    Affiche les informations détaillées
    d'un niveau académique.
    """

    # --------------------------------------------------------
    # RÉCUPÉRATION DU NIVEAU
    # --------------------------------------------------------

    niveau = get_object_or_404(
        Niveau,
        id=niveau_id
    )

    # --------------------------------------------------------
    # RÉCUPÉRATION DES CLASSES ASSOCIÉES
    # --------------------------------------------------------

    classes = (
        niveau.classes
        .select_related(
            "annee",
            "section",
        )
        .order_by(
            "-annee__date_debut",
            "code",
        )
    )

    # --------------------------------------------------------
    # NOMBRE DE CLASSES
    # --------------------------------------------------------

    nombre_classes = classes.count()

    # --------------------------------------------------------
    # CONTEXTE
    # --------------------------------------------------------

    context = {
        "niveau": niveau,
        "classes": classes,
        "nombre_classes": nombre_classes,
    }

    return render(
        request,
        "annee/detail_niveau.html",
        context,
    )

@permission_requise("niveau.modifier")
def modifier_niveau(request, niveau_id):
    """
    Permet de modifier un niveau académique.
    """

    niveau = get_object_or_404(
        Niveau,
        id=niveau_id
    )

    if request.method == "POST":

        form = NiveauForm(
            request.POST,
            instance=niveau
        )

        if form.is_valid():

            # ------------------------------------------------
            # RÉCUPÉRATION DES NOUVELLES DONNÉES
            # ------------------------------------------------

            nouveau_est_ecole_base = (
                form.cleaned_data["est_ecole_base"]
            )

            # ------------------------------------------------
            # VÉRIFICATION DU CHANGEMENT VERS ÉCOLE DE BASE
            # ------------------------------------------------

            if (
                nouveau_est_ecole_base
                and not niveau.est_ecole_base
            ):

                classes_avec_section = (
                    niveau.classes.filter(
                        section__isnull=False
                    )
                )

                if classes_avec_section.exists():

                    form.add_error(
                        "est_ecole_base",
                        "Impossible de transformer ce niveau "
                        "en niveau de l'École de base car certaines "
                        "classes associées possèdent une section."
                    )

                    return render(
                        request,
                        "annee/modifier_niveau.html",
                        {
                            "form": form,
                            "niveau": niveau,
                        }
                    )

            # ------------------------------------------------
            # VÉRIFICATION DU CHANGEMENT VERS NIVEAU SPÉCIALISÉ
            # ------------------------------------------------

            if (
                not nouveau_est_ecole_base
                and niveau.est_ecole_base
            ):

                classes_sans_section = (
                    niveau.classes.filter(
                        section__isnull=True
                    )
                )

                if classes_sans_section.exists():

                    form.add_error(
                        "est_ecole_base",
                        "Impossible de transformer ce niveau "
                        "en niveau avec section car certaines "
                        "classes associées n'ont pas de section."
                    )

                    return render(
                        request,
                        "annee/modifier_niveau.html",
                        {
                            "form": form,
                            "niveau": niveau,
                        }
                    )

            # ------------------------------------------------
            # ENREGISTREMENT
            # ------------------------------------------------

            niveau = form.save()

            message_vers_notification(request, 'SUCCESS', f"Le niveau « {niveau.libelle} » "
                "a été modifié avec succès.", f"Le niveau « {niveau.libelle} » "
                "a été modifié avec succès.")

            return redirect(
                "detail_niveau",
                niveau_id=niveau.id
            )

    else:

        form = NiveauForm(
            instance=niveau
        )

    return render(
        request,
        "annee/modifier_niveau.html",
        {
            "form": form,
            "niveau": niveau,
        }
    )

@permission_requise("niveau.modifier")
def activer_desactiver_niveau(request, niveau_id):

    niveau = get_object_or_404(
        Niveau,
        id=niveau_id
    )

    if request.method == "POST":

        # ================================================
        # CAS 1 : LE NIVEAU EST ACTUELLEMENT ACTIF
        # → Tentative de désactivation
        # ================================================

        if niveau.actif:

            # Vérifier s'il existe encore des classes actives
            classes_actives = niveau.classes.filter(
                actif=True
            )

            if classes_actives.exists():

                message_vers_notification(request, 'ERROR', "Impossible de désactiver ce niveau car "
                    "il est encore utilisé par une ou plusieurs "
                    "classes actives.", "Impossible de désactiver ce niveau car "
                    "il est encore utilisé par une ou plusieurs "
                    "classes actives.")

                return redirect(
                    "detail_niveau",
                    niveau_id=niveau.id
                )

            niveau.actif = False

            niveau.save(
                update_fields=["actif"]
            )

            message_vers_notification(request, 'SUCCESS', f"Le niveau « {niveau.libelle} » "
                "a été désactivé avec succès.", f"Le niveau « {niveau.libelle} » "
                "a été désactivé avec succès.")

        # ================================================
        # CAS 2 : LE NIVEAU EST DÉSACTIVÉ
        # → Activation
        # ================================================

        else:

            niveau.actif = True

            niveau.save(
                update_fields=["actif"]
            )

            message_vers_notification(request, 'SUCCESS', f"Le niveau « {niveau.libelle} » "
                "a été activé avec succès.", f"Le niveau « {niveau.libelle} » "
                "a été activé avec succès.")

        return redirect(
            "detail_niveau",
            niveau_id=niveau.id
        )

    # ====================================================
    # AFFICHAGE DE LA PAGE
    # ====================================================

    return render(
        request,
        "annee/activer_desactiver_niveau.html",
        {
            "niveau": niveau,
        }
    )

@permission_requise("classe.consulter")
def liste_classes(request):

    # =========================================================
    # RÉCUPÉRATION DES CLASSES
    # =========================================================

    classes = Classe.objects.select_related(
        "annee",
        "niveau",
        "section",
    ).all()


    # =========================================================
    # RÉCUPÉRATION DES FILTRES
    # =========================================================

    annee_selectionnee = request.GET.get("annee", "")
    niveau_selectionne = request.GET.get("niveau", "")
    section_selectionnee = request.GET.get("section", "")
    statut_selectionne = request.GET.get("statut", "")


    # =========================================================
    # FILTRE PAR ANNÉE
    # =========================================================

    if annee_selectionnee:

        classes = classes.filter(
            annee_id=annee_selectionnee
        )


    # =========================================================
    # FILTRE PAR NIVEAU
    # =========================================================

    if niveau_selectionne:

        classes = classes.filter(
            niveau_id=niveau_selectionne
        )


    # =========================================================
    # FILTRE PAR SECTION
    # =========================================================

    if section_selectionnee:

        classes = classes.filter(
            section_id=section_selectionnee
        )


    # =========================================================
    # FILTRE PAR STATUT
    # =========================================================

    if statut_selectionne == "actif":

        classes = classes.filter(
            actif=True
        )

    elif statut_selectionne == "inactif":

        classes = classes.filter(
            actif=False
        )


    # =========================================================
    # TRI
    # =========================================================

    classes = classes.order_by(
        "-annee__date_debut",
        "niveau__ordre",
        "section__libelle",
        "code",
    )


    # =========================================================
    # STATISTIQUES
    # =========================================================

    total_classes = classes.count()

    total_classes_actives = classes.filter(
        actif=True
    ).count()

    total_classes_desactivees = classes.filter(
        actif=False
    ).count()


    # =========================================================
    # DONNÉES POUR LES FILTRES
    # =========================================================

    annees = AnneeScolaire.objects.all().order_by(
        "-date_debut"
    )

    niveaux = Niveau.objects.all().order_by(
        "ordre"
    )

    sections = Section.objects.all().order_by(
        "libelle"
    )


    # =========================================================
    # CONTEXTE
    # =========================================================

    contexte = {

        # Liste des classes
        "classes": classes,

        # Statistiques
        "total_classes": total_classes,
        "total_classes_actives": total_classes_actives,
        "total_classes_desactivees":
            total_classes_desactivees,

        # Données des filtres
        "annees": annees,
        "niveaux": niveaux,
        "sections": sections,

        # Valeurs actuellement sélectionnées
        "annee_selectionnee":
            annee_selectionnee,

        "niveau_selectionne":
            niveau_selectionne,

        "section_selectionnee":
            section_selectionnee,

        "statut_selectionne":
            statut_selectionne,
    }


    return render(
        request,
        "annee/liste_classes.html",
        contexte
    )

@permission_requise("classe.creer")
def creer_classe(request):

    if request.method == "POST":

        form = ClasseForm(request.POST)

        if form.is_valid():

            classe = form.save()

            message_vers_notification(request, 'SUCCESS', f"La classe « {classe.libelle} » "
                "a été créée avec succès.", f"La classe « {classe.libelle} » "
                "a été créée avec succès.")

            return redirect("liste_classes")

        else:

            message_vers_notification(request, 'ERROR', "Veuillez corriger les erreurs du formulaire.", "Veuillez corriger les erreurs du formulaire.")

    else:

        form = ClasseForm()


    niveaux_ecole_base = Niveau.objects.filter(
        est_ecole_base=True,
        actif=True
    ).order_by("ordre")


    return render(
        request,
        "annee/creer_classe.html",
        {
            "form": form,
            "niveaux_ecole_base": niveaux_ecole_base,
        }
    )

@permission_requise("classe.consulter")
def detail_classe(request, classe_id):

    # =====================================================
    # RÉCUPÉRATION DE LA CLASSE
    # =====================================================

    classe = get_object_or_404(
        Classe.objects.select_related(
            "annee",
            "niveau",
            "section",
        ),
        id=classe_id
    )


    # =====================================================
    # DONNÉES TEMPORAIRES
    #
    # Ces données seront reliées aux futurs modules :
    # - inscriptions
    # - enseignants
    # - titulaire
    # =====================================================

    nombre_eleves = 0
    nombre_enseignants = 0
    titulaire = None


    # =====================================================
    # CONTEXTE
    # =====================================================

    contexte = {

        "classe": classe,
        "nombre_eleves": nombre_eleves,
        "nombre_enseignants": nombre_enseignants,
        "titulaire": titulaire,
    }

    return render(
        request,
        "annee/detail_classe.html",
        contexte
    )

@permission_requise("classe.modifier")
def modifier_classe(request, classe_id):

    # =====================================================
    # RÉCUPÉRATION DE LA CLASSE
    # =====================================================

    classe = get_object_or_404(
        Classe,
        id=classe_id
    )


    # =====================================================
    # TRAITEMENT DU FORMULAIRE
    # =====================================================

    if request.method == "POST":

        form = ClasseForm(
            request.POST,
            instance=classe
        )

        if form.is_valid():

            form.save()

            message_vers_notification(request, 'SUCCESS', f"La classe « {classe.libelle} » "
                "a été modifiée avec succès.", f"La classe « {classe.libelle} » "
                "a été modifiée avec succès.")

            return redirect(
                "detail_classe",
                classe_id=classe.id
            )

        else:

            message_vers_notification(request, 'ERROR', "Veuillez corriger les erreurs "
                "avant d'enregistrer.", "Veuillez corriger les erreurs "
                "avant d'enregistrer.")


    # =====================================================
    # AFFICHAGE DU FORMULAIRE
    # =====================================================

    else:

        form = ClasseForm(
            instance=classe
        )


    # =====================================================
    # NIVEAUX DE L'ÉCOLE DE BASE
    #
    # Utilisés par le JavaScript de modifier_classe.html
    # =====================================================

    niveaux_ecole_base = Niveau.objects.filter(
        est_ecole_base=True,
        actif=True
    ).order_by(
        "ordre"
    )


    # =====================================================
    # CONTEXTE
    # =====================================================

    contexte = {

        "classe": classe,

        "form": form,

        "niveaux_ecole_base":
            niveaux_ecole_base,
    }


    return render(
        request,
        "annee/modifier_classe.html",
        contexte
    )
    
@permission_requise("classe.modifier")
def activer_desactiver_classe(request, classe_id):

    # =====================================================
    # RÉCUPÉRATION DE LA CLASSE
    # =====================================================

    classe = get_object_or_404(
        Classe.objects.select_related(
            "annee",
            "niveau",
            "section",
        ),
        id=classe_id
    )
    # =====================================================
    # CONFIRMATION DU CHANGEMENT
    # =====================================================

    if request.method == "POST":

        # -------------------------------------------------
        # CAS 1 : LA CLASSE EST ACTIVE
        # -------------------------------------------------

        if classe.actif:

            classe.actif = False

            classe.save(
                update_fields=["actif"]
            )

            message_vers_notification(request, 'SUCCESS', f"La classe « {classe.libelle} » "
                "a été désactivée avec succès.", f"La classe « {classe.libelle} » "
                "a été désactivée avec succès.")


        # -------------------------------------------------
        # CAS 2 : LA CLASSE EST DÉSACTIVÉE
        # -------------------------------------------------

        else:

            classe.actif = True

            classe.save(
                update_fields=["actif"]
            )

            message_vers_notification(request, 'SUCCESS', f"La classe « {classe.libelle} » "
                "a été activée avec succès.", f"La classe « {classe.libelle} » "
                "a été activée avec succès.")


        # -------------------------------------------------
        # REDIRECTION
        # -------------------------------------------------

        return redirect(
            "detail_classe",
            classe_id=classe.id
        )


    # =====================================================
    # AFFICHAGE DE LA PAGE DE CONFIRMATION
    # =====================================================

    return render(
        request,
        "annee/activer_desactiver_classe.html",
        {
            "classe": classe,
        }
    )

#@permission_requise("matiere.voir")
@permission_requise("matiere.consulter")
def liste_matieres(request):

    # =====================================================
    # RÉCUPÉRATION DES MATIÈRES
    # =====================================================

    matieres = Matiere.objects.all().order_by(
        "libelle"
    )


    # =====================================================
    # STATISTIQUES
    # =====================================================

    total_matieres = matieres.count()

    matieres_actives = matieres.filter(
        actif=True
    ).count()

    matieres_inactives = matieres.filter(
        actif=False
    ).count()


    # =====================================================
    # CONTEXTE
    # =====================================================

    contexte = {

        "matieres": matieres,

        "total_matieres": total_matieres,

        "matieres_actives": matieres_actives,

        "matieres_inactives": matieres_inactives,

    }


    # =====================================================
    # AFFICHAGE
    # =====================================================

    return render(
        request,
        "annee/liste_matiere.html",
        contexte
    )

def _duree_creneau_en_heures(creneau):
    """Duree d'un creneau, exprimee en heures decimales.

    Le volume d'un cours se compte en heures hebdomadaires alors que la
    grille horaire travaille en creneaux : la conversion est necessaire
    pour savoir combien d'heures restent a programmer.
    """
    minutes = (
        datetime.combine(date.today(), creneau.heure_fin)
        - datetime.combine(date.today(), creneau.heure_debut)
    ).total_seconds() / 60

    return round(minutes / 60, 2)


def _heures_programmees(affectation_matiere):
    """Heures deja placees au planning pour une affectation de matiere."""
    total = Decimal("0")

    repartitions = (
        RepartitionHoraire.objects
        .filter(
            affectation__affectation_matiere=affectation_matiere,
            actif=True,
        )
        .select_related("creneau")
    )

    for repartition in repartitions:
        total += Decimal(
            str(_duree_creneau_en_heures(repartition.creneau))
        )

    return total


def _contexte_programmation_cours(request, utilisateur):
    """Donnees necessaires au template de programmation des cours.

    Le template attend quatre variables : l'annee active, les classes
    candidates, la classe eventuellement preselectionnee via ?classe_id=
    et les cours deja affectes a cette classe.
    """
    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    classes = (
        Classe.objects
        .select_related("annee", "niveau", "section")
        .filter(actif=True)
    )

    if annee_active:
        classes = classes.filter(annee=annee_active)

    classes = classes.order_by("niveau__ordre", "code")

    classe_preselectionnee = None
    classe_id = request.GET.get("classe_id") or request.GET.get("classe")

    if classe_id:
        classe_preselectionnee = classes.filter(id=classe_id).first()

    if classe_preselectionnee and not annee_active:
        annee_active = classe_preselectionnee.annee

    # Le popup de cours et le compteur de sa liste doivent annoncer le
    # meme total : ne lister que les cours saisis a la main ferait
    # croire a une classe sans programme officiel.
    cours_classe = (
        _lignes_cours_classe(classe_preselectionnee)
        if classe_preselectionnee
        else []
    )

    return {
        "utilisateur": utilisateur,
        "annee_active": annee_active,
        "classes_pour_affectation": classes,
        "classe_preselectionnee": classe_preselectionnee,
        "matiere_a_programmer": cours_classe,
        "nb_cours_programme": len(cours_classe),
    }


def _programmations_depuis_post(request):
    """Relit le JSON envoye par le formulaire de programmation."""
    bruts = request.POST.get("programmations", "[]")

    try:
        donnees = json.loads(bruts)
    except (TypeError, ValueError):
        return []

    if not isinstance(donnees, list):
        return []

    return [item for item in donnees if isinstance(item, dict)]


@permission_requise("matiere.creer")
def programmation_cours(request):
    """Programmation des cours d'une classe dans la grille horaire.

    GET  : affiche la page avec les classes de l'annee active.
    POST : enregistre les creneaux coches par l'utilisateur sous forme
           de repartitions horaires, apres controle des regles metier
           (creneau libre pour la classe, enseignant libre, annee
           compatible).
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    contexte = _contexte_programmation_cours(request, utilisateur)

    if request.method != "POST":
        return render(
            request,
            "annee/creer_matiere.html",
            contexte,
        )

    # =========================================================
    # ENREGISTREMENT
    # =========================================================

    programmees = 0
    erreurs = []

    for item in _programmations_depuis_post(request):

        affectation_id = item.get("affectation_id")
        affectation = Affectation.objects.filter(
            id=affectation_id,
            actif=True,
        ).select_related(
            "enseignant",
            "affectation_matiere",
            "affectation_matiere__classe",
        ).first()

        if not affectation:
            erreurs.append(
                "Un cours selectionne ne correspond plus a "
                "une affectation active."
            )
            continue

        for creneau_item in item.get("creneaux") or []:
            if not isinstance(creneau_item, dict):
                continue

            repartition = RepartitionHoraire(
                affectation=affectation,
                jour=creneau_item.get("jour", ""),
                creneau_id=creneau_item.get("creneau_id"),
            )

            try:
                repartition.full_clean()
                repartition.save()
                programmees += 1
            except ValidationError as erreur:
                erreurs.append(
                    "; ".join(
                        " ".join(str(v) for v in valeur)
                        for valeur in erreur.message_dict.values()
                    )
                )
            except (IntegrityError, ValueError, TypeError):
                erreurs.append(
                    "Un cours a ete enregistre deux fois dans le "
                    "meme creneau."
                )

    if programmees and not erreurs:
        message_vers_notification(
            request,
            "SUCCESS",
            f"{programmees} creneau(x) ont ete programme(s) avec succes.",
            f"{programmees} creneau(x) ont ete programme(s) avec succes.",
        )
    elif programmees:
        message_vers_notification(
            request,
            "WARNING",
            f"{programmees} creneau(x) enregistre(s), mais "
            f"{len(erreurs)} ont ete refuses.",
            f"{programmees} creneau(x) enregistre(s), mais "
            f"{len(erreurs)} ont ete refuses.",
        )
    elif erreurs:
        message_vers_notification(
            request,
            "ERROR",
            erreurs[0][:200],
            erreurs[0][:200],
        )

    return redirect("programmation_cours")


#@permission_requise("matiere.creer")
@permission_requise("matiere.creer")
def creer_matiere(request):

    # =====================================================
    # PROGRAMMATION DES COURS
    #
    # Cette route Pointait historiquement sur une page de creation
    # de matiere alors que son template est entierement une page de
    # programmation par classe. Elle est desormais un simple alias
    # de la vue dediee, pour que les anciens liens continuent de
    # fonctionner.
    # =====================================================

    return programmation_cours(request)

#@permission_requise("matiere.voir")
@permission_requise("matiere.consulter")
def detail_matiere(request, matiere_id):

    matiere = get_object_or_404(
        Matiere,
        id=matiere_id
    )

    return render(
        request,
        "annee/detail_matiere.html",
        {
            "matiere": matiere,
        }
    )

#@permission_requise("matiere.modifier")
@permission_requise("matiere.modifier")
def modifier_matiere(request, matiere_id):

    # =====================================================
    # RÉCUPÉRATION DE LA MATIÈRE
    # =====================================================

    matiere = get_object_or_404(
        Matiere,
        id=matiere_id
    )


    # =====================================================
    # TRAITEMENT DU FORMULAIRE
    # =====================================================

    if request.method == "POST":

        form = MatiereForm(
            request.POST,
            instance=matiere
        )

        if form.is_valid():

            matiere = form.save()

            message_vers_notification(request, 'SUCCESS', f"La matière « {matiere.libelle} » "
                "a été modifiée avec succès.", f"La matière « {matiere.libelle} » "
                "a été modifiée avec succès.")

            return redirect(
                "detail_matiere",
                matiere_id=matiere.id
            )

        else:

            message_vers_notification(request, 'ERROR', "Veuillez corriger les erreurs "
                "du formulaire.", "Veuillez corriger les erreurs "
                "du formulaire.")


    # =====================================================
    # AFFICHAGE INITIAL
    # =====================================================

    else:

        form = MatiereForm(
            instance=matiere
        )


    # =====================================================
    # AFFICHAGE DE LA PAGE
    # =====================================================

    contexte = {
        "matiere": matiere,
        "form": form,
    }


    return render(
        request,
        "annee/modifier_matiere.html",
        contexte
    )

@permission_requise("matiere.modifier")
def activer_desactiver_matiere(
    request,
    matiere_id
):

    # =====================================================
    # RÉCUPÉRATION DE LA MATIÈRE
    # =====================================================

    matiere = get_object_or_404(
        Matiere,
        id=matiere_id
    )


    # =====================================================
    # CONFIRMATION DU CHANGEMENT
    # =====================================================

    if request.method == "POST":

        # -------------------------------------------------
        # DÉSACTIVATION
        # -------------------------------------------------

        if matiere.actif:

            matiere.actif = False

            message = (
                f"La matière « {matiere.libelle} » "
                "a été désactivée avec succès."
            )


        # -------------------------------------------------
        # ACTIVATION
        # -------------------------------------------------

        else:

            matiere.actif = True

            message = (
                f"La matière « {matiere.libelle} » "
                "a été activée avec succès."
            )


        # -------------------------------------------------
        # ENREGISTREMENT
        # -------------------------------------------------

        matiere.save()

        message_vers_notification(request, 'SUCCESS', message, message)


        return redirect(
            "detail_matiere",
            matiere_id=matiere.id
        )


    # =====================================================
    # AFFICHAGE DE LA PAGE DE CONFIRMATION
    # =====================================================

    contexte = {
        "matiere": matiere,
    }


    return render(
        request,
        "annee/activer_desactiver_matiere.html",
        contexte
    )

#@permission_requise("affectation_matiere.voir")
@permission_requise("affectation.consulter")
def liste_affectations_matieres(request):

    # =====================================================
    # RÉCUPÉRATION DES FILTRES
    # =====================================================

    classe_selectionnee = request.GET.get(
        "classe",
        ""
    )

    matiere_selectionnee = request.GET.get(
        "matiere",
        ""
    )


    # =====================================================
    # LISTE DES AFFECTATIONS
    # =====================================================

    affectations = (
        AffectationMatiere.objects
        .select_related(
            "classe",
            "classe__annee",
            "classe__niveau",
            "classe__section",
            "matiere",
        )
        .all()
    )


    # =====================================================
    # FILTRE PAR CLASSE
    # =====================================================

    if classe_selectionnee:

        affectations = affectations.filter(
            classe_id=classe_selectionnee
        )


    # =====================================================
    # FILTRE PAR MATIÈRE
    # =====================================================

    if matiere_selectionnee:

        affectations = affectations.filter(
            matiere_id=matiere_selectionnee
        )


    # =====================================================
    # LISTES POUR LES FILTRES
    # =====================================================

    classes = (
        Classe.objects
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

    matieres = (
        Matiere.objects
        .order_by(
            "libelle"
        )
    )


    # =====================================================
    # CONTEXTE
    # =====================================================

    contexte = {
        "affectations": affectations,
        "classes": classes,
        "matieres": matieres,
        "classe_selectionnee": classe_selectionnee,
        "matiere_selectionnee": matiere_selectionnee,
    }


    # =====================================================
    # AFFICHAGE
    # =====================================================

    return render(
        request,
        "Gestion/liste_affectations_matieres.html",
        contexte
    )

def _initial_affectation_matiere(request):
    """Classe et annee pre-selectionnees a partir de ?classe_id=<id>.

    La page de gestion des matieres par classe ouvre la creation
    d'affectation en passant l'identifiant de la classe dans l'URL. Sans ce
    traitement, la classe saisie sur la carte etait perdue et l'utilisateur
    devait la reselectionner a la main.
    """
    classe_id = request.GET.get("classe_id") or request.GET.get("classe")
    if not classe_id:
        return {}

    classe = Classe.objects.filter(id=classe_id, actif=True).first()
    if not classe:
        return {}

    return {
        "classe": classe.id,
        "annee": classe.annee_id,
    }


#@permission_requise("affectation_matiere.creer")
@permission_requise("affectation.creer")
def creer_affectation_matiere(request):
    if request.method == "POST":
        form = AffectationMatiereForm(
            request.POST
        )

        if form.is_valid():
            affectation = form.save()

            message_vers_notification(request, 'SUCCESS', (
                    f"La matière « {affectation.matiere.libelle} » "
                    f"a été affectée à la classe "
                    f"« {affectation.classe.libelle} » "
                    f"avec succès."
                ), (
                    f"La matière « {affectation.matiere.libelle} » "
                    f"a été affectée à la classe "
                    f"« {affectation.classe.libelle} » "
                    f"avec succès."
                ))

            return redirect(
                "liste_affectations_matieres"
            )

        message_vers_notification(request, 'ERROR', "Veuillez corriger les erreurs du formulaire.", "Veuillez corriger les erreurs du formulaire.")

    else:
        form = AffectationMatiereForm(
            initial=_initial_affectation_matiere(request)
        )

    return render(
        request,
        "Gestion/creer_affectation_matiere.html",
        {
            "form": form,
        }
    )
    
#@permission_requise("affectation_matiere.voir")
@permission_requise("affectation.consulter")
def detail_affectation_matiere(
    request,
    affectation_id
):

    affectation = get_object_or_404(
        AffectationMatiere.objects.select_related(
            "classe",
            "classe__annee",
            "classe__niveau",
            "classe__section",
            "matiere",
        ),
        id=affectation_id
    )


    return render(
        request,
        "Gestion/detail_affectation_matiere.html",
        {
            "affectation": affectation,
        }
    )

#@permission_requise("affectation_matiere.modifier")
@permission_requise("affectation.modifier")
def modifier_affectation_matiere(
    request,
    affectation_id
):

    # =====================================================
    # RÉCUPÉRATION DE L'AFFECTATION
    # =====================================================

    affectation = get_object_or_404(
        AffectationMatiere,
        id=affectation_id
    )


    # =====================================================
    # TRAITEMENT DU FORMULAIRE
    # =====================================================

    if request.method == "POST":

        form = AffectationMatiereForm(
            request.POST,
            instance=affectation
        )

        if form.is_valid():

            affectation = form.save()


            # ---------------------------------------------
            # MESSAGE DE SUCCÈS
            # ---------------------------------------------

            message_vers_notification(request, 'SUCCESS', "L'affectation a été modifiée avec succès.", "L'affectation a été modifiée avec succès.")


            # ---------------------------------------------
            # REDIRECTION
            # ---------------------------------------------

            return redirect(
                "detail_affectation_matiere",
                affectation_id=affectation.id
            )

        else:

            message_vers_notification(request, 'ERROR', "Veuillez corriger les erreurs du formulaire.", "Veuillez corriger les erreurs du formulaire.")


    # =====================================================
    # AFFICHAGE INITIAL
    # =====================================================

    else:

        form = AffectationMatiereForm(
            instance=affectation
        )


    # =====================================================
    # AFFICHAGE
    # =====================================================

    return render(
        request,
        "Gestion/modifier_affectation_matiere.html",
        {
            "form": form,
            "affectation": affectation,
        }
    )

#@permission_requise("affectation_matiere.modifier")
@permission_requise("affectation.desactiver")
def activer_desactiver_affectation_matiere(
    request,
    affectation_id
):

    # =====================================================
    # RÉCUPÉRATION DE L'AFFECTATION
    # =====================================================

    affectation = get_object_or_404(
        AffectationMatiere,
        id=affectation_id
    )


    # =====================================================
    # CONFIRMATION DE L'ACTION
    # =====================================================

    if request.method == "POST":

        # -------------------------------------------------
        # DÉSACTIVATION
        # -------------------------------------------------

        if affectation.actif:

            affectation.actif = False

            message = (
                f"L'affectation de la matière "
                f"« {affectation.matiere.libelle} » "
                f"à la classe "
                f"« {affectation.classe.libelle} » "
                f"a été désactivée avec succès."
            )


        # -------------------------------------------------
        # ACTIVATION
        # -------------------------------------------------

        else:

            affectation.actif = True

            message = (
                f"L'affectation de la matière "
                f"« {affectation.matiere.libelle} » "
                f"à la classe "
                f"« {affectation.classe.libelle} » "
                f"a été activée avec succès."
            )


        # -------------------------------------------------
        # ENREGISTREMENT
        # -------------------------------------------------

        affectation.save(
            update_fields=["actif"]
        )


        # -------------------------------------------------
        # MESSAGE
        # -------------------------------------------------

        message_vers_notification(request, 'SUCCESS', message, message)


        # -------------------------------------------------
        # REDIRECTION
        # -------------------------------------------------

        return redirect(
            "detail_affectation_matiere",
            affectation_id=affectation.id
        )


    # =====================================================
    # AFFICHAGE DE LA CONFIRMATION
    # =====================================================

    return render(
        request,
        "Gestion/activer_desactiver_affectation_matiere.html",
        {
            "affectation": affectation,
        }
    )
    
def liste_enseignants(request):

    enseignants = (
        Enseignant.objects
        .select_related("utilisateur")
        .order_by(
            "utilisateur__nom",
            "utilisateur__prenom",
        )
    )

    return render(
        request,
        "enseignant/liste_enseignants.html",
        {
            "enseignants": enseignants,
        }
    )


def impression_liste_enseignants(request):
    """Liste des enseignants, mise en page A4 paysage.

    Le volume horaire est additionne par matiere : un enseignant porte
    plusieurs classes pour une meme matiere, et le total doit alors
    compter les heures reellement vues, pas le nombre d'affectations.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    enseignants = list(
        Enseignant.objects
        .select_related("utilisateur")
        .prefetch_related(
            "affectations__affectation_matiere__classe",
            "affectations__affectation_matiere__matiere",
        )
        .order_by("utilisateur__nom", "utilisateur__prenom")
    )

    total_heures = 0

    for enseignant in enseignants:
        affectations = [
            affectation
            for affectation in enseignant.affectations.all()
            if affectation.actif
            and affectation.affectation_matiere_id
        ]

        enseignant.nb_affectations = len(affectations)

        # Le template ne sait pas dedupliquer : les classes sont
        # preparees ici, triees et sans repetition.
        classes = []
        for affectation in affectations:
            classe = affectation.affectation_matiere.classe
            if classe not in classes:
                classes.append(classe)
        enseignant.classes = sorted(
            classes, key=lambda classe: classe.libelle
        )

        enseignant.total_heures = sum(
            affectation.affectation_matiere.heures_par_semaine
            for affectation in affectations
        )
        total_heures += enseignant.total_heures

        enseignant.date_entree = (
            min(
                affectation.date_creation
                for affectation in affectations
            )
            if affectations
            else None
        )

    annee = (
        AnneeScolaire.objects
        .filter(statut=AnneeScolaire.ACTIVE)
        .first()
    )

    return render(
        request,
        "enseignant/impression_liste_enseignants.html",
        {
            "utilisateur": utilisateur,
            "enseignants": enseignants,
            "annee": annee,
            "nb_actifs": sum(
                1
                for enseignant in enseignants
                if enseignant.actif and enseignant.utilisateur.actif
            ),
            "nb_inactifs": len(enseignants) - sum(
                1
                for enseignant in enseignants
                if enseignant.actif and enseignant.utilisateur.actif
            ),
            "nb_affectes": sum(
                1
                for enseignant in enseignants
                if enseignant.nb_affectations
            ),
            "total_heures": total_heures,
            "maintenant": timezone.now(),
        }
    )


def creer_enseignant(request):

    if request.method == "POST":

        form = EnseignantForm(
            request.POST,
            request.FILES
        )


        if form.is_valid():

            try:

                with transaction.atomic():

                    # =================================================
                    # CRÉATION DE L'UTILISATEUR
                    # =================================================

                    utilisateur = Utilisateur.objects.create(
                        nom=form.cleaned_data["nom"],
                        postnom=(
                            form.cleaned_data["postnom"]
                            or None
                        ),
                        prenom=form.cleaned_data["prenom"],
                        email=(
                            form.cleaned_data["email"]
                            or None
                        ),
                        telephone=(
                            form.cleaned_data["telephone"]
                            or None
                        ),
                        photo_profil=(
                            form.cleaned_data["photo_profil"]
                        ),
                        actif=True,
                    )


                    # =================================================
                    # ENREGISTREMENT SÉCURISÉ DU MOT DE PASSE
                    # =================================================

                    utilisateur.set_password(
                        form.cleaned_data["mot_de_passe"]
                    )

                    utilisateur.save()


                    # =================================================
                    # CRÉATION DE L'ENSEIGNANT
                    # =================================================

                    enseignant = Enseignant.objects.create(
                        utilisateur=utilisateur,
                        matricule=(
                            form.cleaned_data["matricule"]
                        ),
                        grade=(
                            form.cleaned_data["grade"]
                            or None
                        ),
                        specialite=(
                            form.cleaned_data["specialite"]
                            or None
                        ),
                        actif=True,
                    )


                # =====================================================
                # MESSAGE DE SUCCÈS
                # =====================================================

                message_vers_notification(request, 'SUCCESS', (
                        "L'enseignant "
                        f"{enseignant.utilisateur.nom} "
                        f"{enseignant.utilisateur.prenom} "
                        "a été créé avec succès."
                    ), (
                        "L'enseignant "
                        f"{enseignant.utilisateur.nom} "
                        f"{enseignant.utilisateur.prenom} "
                        "a été créé avec succès."
                    ))


                return redirect(
                    "liste_enseignants"
                )


            except Exception:

                message_vers_notification(request, 'ERROR', (
                        "Une erreur est survenue lors "
                        "de la création de l'enseignant."
                    ), (
                        "Une erreur est survenue lors "
                        "de la création de l'enseignant."
                    ))


    else:

        form = EnseignantForm()


    return render(
        request,
        "enseignant/creer_enseignant.html",
        {
            "form": form,
        }
    )

def detail_enseignant(request, enseignant_id):

    enseignant = get_object_or_404(
        Enseignant.objects.select_related(
            "utilisateur"
        ),
        id=enseignant_id
    )

    return render(
        request,
        "enseignant/detail_enseignant.html",
        {
            "enseignant": enseignant,
        }
    )

def modifier_enseignant(request, enseignant_id):

    # =========================================================
    # RÉCUPÉRATION DE L'ENSEIGNANT
    # =========================================================

    enseignant = get_object_or_404(
        Enseignant.objects.select_related(
            "utilisateur"
        ),
        id=enseignant_id
    )


    utilisateur = enseignant.utilisateur


    # =========================================================
    # TRAITEMENT DU FORMULAIRE
    # =========================================================

    if request.method == "POST":

        form = EnseignantForm(
            request.POST,
            request.FILES,
            enseignant=enseignant
        )


        if form.is_valid():

            try:

                # Les modifications de l'utilisateur et
                # de l'enseignant doivent réussir ensemble.

                with transaction.atomic():

                    # -------------------------------------------------
                    # INFORMATIONS PERSONNELLES
                    # -------------------------------------------------

                    utilisateur.nom = (
                        form.cleaned_data["nom"]
                    )


                    utilisateur.postnom = (
                        form.cleaned_data["postnom"]
                        or None
                    )


                    utilisateur.prenom = (
                        form.cleaned_data["prenom"]
                    )


                    utilisateur.email = (
                        form.cleaned_data["email"]
                        or None
                    )


                    utilisateur.telephone = (
                        form.cleaned_data["telephone"]
                        or None
                    )


                    # -------------------------------------------------
                    # PHOTO DE PROFIL
                    # -------------------------------------------------

                    if form.cleaned_data.get(
                        "photo_profil"
                    ):

                        utilisateur.photo_profil = (
                            form.cleaned_data[
                                "photo_profil"
                            ]
                        )


                    # -------------------------------------------------
                    # MODIFICATION DU MOT DE PASSE
                    # -------------------------------------------------

                    nouveau_mot_de_passe = (
                        form.cleaned_data.get(
                            "mot_de_passe"
                        )
                    )


                    # Le mot de passe est modifié uniquement
                    # si une nouvelle valeur a été saisie.

                    if nouveau_mot_de_passe:

                        utilisateur.set_password(
                            nouveau_mot_de_passe
                        )


                    # -------------------------------------------------
                    # ENREGISTREMENT DE L'UTILISATEUR
                    # -------------------------------------------------

                    utilisateur.save()


                    # =================================================
                    # INFORMATIONS PROFESSIONNELLES
                    # =================================================

                    enseignant.matricule = (
                        form.cleaned_data["matricule"]
                    )


                    enseignant.grade = (
                        form.cleaned_data["grade"]
                        or None
                    )


                    enseignant.specialite = (
                        form.cleaned_data["specialite"]
                        or None
                    )


                    # -------------------------------------------------
                    # ENREGISTREMENT DE L'ENSEIGNANT
                    # -------------------------------------------------

                    enseignant.save()


                # =====================================================
                # MESSAGE DE SUCCÈS
                # =====================================================

                message_vers_notification(request, 'SUCCESS', (
                        "Les informations de l'enseignant ont "
                        "été modifiées avec succès."
                    ), (
                        "Les informations de l'enseignant ont "
                        "été modifiées avec succès."
                    ))


                return redirect(
                    "detail_enseignant",
                    enseignant_id=enseignant.id
                )


            except Exception:

                message_vers_notification(request, 'ERROR', (
                        "Une erreur est survenue lors de la "
                        "modification de l'enseignant."
                    ), (
                        "Une erreur est survenue lors de la "
                        "modification de l'enseignant."
                    ))


    # =========================================================
    # AFFICHAGE INITIAL DU FORMULAIRE
    # =========================================================

    else:

        form = EnseignantForm(
            enseignant=enseignant
        )


    return render(
        request,
        "enseignant/modifier_enseignant.html",
        {
            "form": form,
            "enseignant": enseignant,
        }
    )


def activer_desactiver_enseignant(request, enseignant_id):

    enseignant = get_object_or_404(
        Enseignant.objects.select_related("utilisateur"),
        id=enseignant_id
    )

    if request.method == "POST":

        with transaction.atomic():

            # Inversion du statut de l'enseignant
            enseignant.actif = not enseignant.actif

            # Synchronisation du statut de l'utilisateur
            enseignant.utilisateur.actif = enseignant.actif

            # Enregistrement des modifications
            enseignant.save()

            enseignant.utilisateur.save()

        if enseignant.actif:

            message_vers_notification(request, 'SUCCESS', "L'enseignant a été activé avec succès.", "L'enseignant a été activé avec succès.")

        else:

            message_vers_notification(request, 'SUCCESS', "L'enseignant a été désactivé avec succès.", "L'enseignant a été désactivé avec succès.")

        return redirect(
            "detail_enseignant",
            enseignant_id=enseignant.id
        )

    return render(
        request,
        "enseignant/activer_desactiver_enseignant.html",
        {
            "enseignant": enseignant,
        }
    )

def ajax_classes_par_annee(request):

    # -----------------------------------------------------
    # RÉCUPÉRATION DE L'ANNÉE
    # -----------------------------------------------------

    annee_id = request.GET.get("annee_id")


    # -----------------------------------------------------
    # VÉRIFICATION
    # -----------------------------------------------------

    if not annee_id:

        return JsonResponse(
            {
                "classes": [],
            }
        )

    try:

        classes = (
            Classe.objects
            .filter(
                annee_id=annee_id
            )
            .order_by("id")
        )


        # -------------------------------------------------
        # CONSTRUCTION DES DONNÉES JSON
        # -------------------------------------------------

        donnees_classes = []

        for classe in classes:

            donnees_classes.append(
                {
                    "id": classe.id,

                    # On utilise __str__ du modèle
                    # pour éviter de supposer que le champ
                    # s'appelle "nom".
                    "nom": str(classe),
                }
            )


        return JsonResponse(
            {
                "classes": donnees_classes,
            }
        )


    # -----------------------------------------------------
    # GESTION DES ERREURS
    # -----------------------------------------------------

    except Exception as error:

        return JsonResponse(
            {
                "classes": [],
                "error": str(error),
            },
            status=400,
        )

# =========================================================
# AJAX : CHARGER LES MATIÈRES D'UNE CLASSE
# =========================================================
def ajax_matieres_par_classe(request):

    # =====================================================
    # RÉCUPÉRATION DES PARAMÈTRES
    # =====================================================

    annee_id = request.GET.get(
        "annee_id"
    )

    classe_id = request.GET.get(
        "classe_id"
    )


    # =====================================================
    # VÉRIFICATION DES PARAMÈTRES
    # =====================================================

    if not annee_id or not classe_id:

        return JsonResponse(
            {
                "matieres": [],
            }
        )


    try:

        # =================================================
        # VÉRIFICATION DE LA CLASSE
        # =================================================

        classe = (
            Classe.objects
            .filter(
                id=classe_id,
                annee_id=annee_id,
                actif=True,
            )
            .first()
        )


        if not classe:

            return JsonResponse(
                {
                    "matieres": [],
                    "error": (
                        "La classe sélectionnée n'appartient "
                        "pas à cette année scolaire ou "
                        "n'est pas active."
                    ),
                },
                status=400,
            )


        # =================================================
        # RÉCUPÉRATION DES MATIÈRES AFFECTÉES
        # =================================================

        affectations_matieres = (
            AffectationMatiere.objects
            .filter(
                classe=classe,
                actif=True,
                matiere__actif=True,
            )
            .select_related(
                "matiere",
                "classe",
            )
            .order_by(
                "matiere__libelle"
            )
        )


        # =================================================
        # CONSTRUCTION DES DONNÉES JSON
        # =================================================

        donnees_matieres = []


        for affectation_matiere in affectations_matieres:

            # =============================================
            # RECHERCHE DE L'AFFECTATION ENSEIGNANT ACTIVE
            # =============================================

            affectation = (
                Affectation.objects
                .filter(
                    affectation_matiere=affectation_matiere,
                    actif=True,
                )
                .select_related(
                    "enseignant",
                    "affectation_matiere",
                )
                .order_by(
                    "id"
                )
                .first()
            )


            # =============================================
            # AUCUN ENSEIGNANT ACTIF
            # =============================================

            if not affectation:

                donnees_matieres.append(
                    {
                        # ---------------------------------
                        # ID DE L'AFFECTATION MATIÈRE
                        # ---------------------------------

                        "id": (
                            affectation_matiere.id
                        ),


                        # ---------------------------------
                        # MATIÈRE
                        # ---------------------------------

                        "matiere_id": (
                            affectation_matiere
                            .matiere
                            .id
                        ),

                        "nom": (
                            affectation_matiere
                            .matiere
                            .libelle
                        ),


                        # ---------------------------------
                        # ENSEIGNANT
                        # ---------------------------------

                        "enseignant": None,

                        "enseignant_id": None,


                        # ---------------------------------
                        # AFFECTATION
                        # ---------------------------------

                        "affectation_id": None,


                        # ---------------------------------
                        # VOLUME HORAIRE
                        # ---------------------------------

                        "heures_par_semaine": (
                            affectation_matiere
                            .heures_par_semaine
                        ),

                        "heures_programmees": 0,

                        "heures_restantes": (
                            affectation_matiere
                            .heures_par_semaine
                        ),


                        # ---------------------------------
                        # PROGRAMMATION
                        # ---------------------------------

                        "peut_programmer": False,

                        "message": (
                            "Aucun enseignant actif "
                            "n'est affecté à cette matière."
                        ),
                    }
                )


                continue


            # =============================================
            # NOMBRE D'HEURES DÉJÀ PROGRAMMÉES
            # =============================================

            heures_programmees = (
                RepartitionHoraire.objects
                .filter(
                    affectation=affectation,
                    actif=True,
                )
                .count()
            )


            # =============================================
            # VOLUME HORAIRE PRÉVU
            # =============================================

            heures_par_semaine = (
                affectation_matiere
                .heures_par_semaine
            )


            # =============================================
            # HEURES RESTANTES
            # =============================================

            heures_restantes = (
                heures_par_semaine
                - heures_programmees
            )


            # ---------------------------------------------
            # ÉVITER UNE VALEUR NÉGATIVE
            # ---------------------------------------------

            if heures_restantes < 0:

                heures_restantes = 0


            # =============================================
            # PEUT ENCORE ÊTRE PROGRAMMÉE
            # =============================================

            peut_programmer = (
                heures_restantes > 0
            )


            # =============================================
            # MESSAGE
            # =============================================

            if peut_programmer:

                message = (
                    f"{heures_restantes} heure(s) "
                    f"restante(s) à programmer."
                )

            else:

                message = (
                    "Le volume horaire hebdomadaire "
                    "de cette matière est déjà atteint."
                )


            # =============================================
            # AJOUT DES DONNÉES
            # =============================================

            donnees_matieres.append(
                {
                    # -------------------------------------
                    # IMPORTANT :
                    #
                    # id = AffectationMatiere
                    #
                    # C'est cette valeur qui sera envoyée
                    # à ajax_creneaux_disponibles sous :
                    #
                    # affectation_matiere_id
                    # -------------------------------------

                    "id": (
                        affectation_matiere.id
                    ),


                    # -------------------------------------
                    # MATIÈRE
                    # -------------------------------------

                    "matiere_id": (
                        affectation_matiere
                        .matiere
                        .id
                    ),

                    "nom": (
                        affectation_matiere
                        .matiere
                        .libelle
                    ),


                    # -------------------------------------
                    # ENSEIGNANT
                    # -------------------------------------

                    "enseignant_id": (
                        affectation
                        .enseignant
                        .id
                    ),

                    "enseignant": str(
                        affectation
                        .enseignant
                    ),


                    # -------------------------------------
                    # AFFECTATION ENSEIGNANT
                    # -------------------------------------

                    "affectation_id": (
                        affectation.id
                    ),


                    # -------------------------------------
                    # VOLUME HORAIRE
                    # -------------------------------------

                    "heures_par_semaine": (
                        heures_par_semaine
                    ),

                    "heures_programmees": (
                        heures_programmees
                    ),

                    "heures_restantes": (
                        heures_restantes
                    ),


                    # -------------------------------------
                    # PROGRAMMATION
                    # -------------------------------------

                    "peut_programmer": (
                        peut_programmer
                    ),

                    "message": (
                        message
                    ),
                }
            )


        # =================================================
        # RÉPONSE JSON
        # =================================================

        return JsonResponse(
            {
                "matieres": (
                    donnees_matieres
                ),
            }
        )


    # =====================================================
    # GESTION DES ERREURS
    # =====================================================

    except Exception as error:

        return JsonResponse(
            {
                "matieres": [],
                "error": str(error),
            },
            status=400,
        )

# =========================================================
# AJAX : CHARGER LES CRÉNEAUX DISPONIBLES
# =========================================================
def ajax_creneaux_disponibles(request):

    # =====================================================
    # RÉCUPÉRATION DES PARAMÈTRES
    # =====================================================

    annee_id = request.GET.get("annee_id")

    classe_id = request.GET.get("classe_id")

    affectation_matiere_id = request.GET.get(
        "affectation_matiere_id"
    )

    jour = request.GET.get("jour")


    # =====================================================
    # VÉRIFICATION DES PARAMÈTRES
    # =====================================================

    if (
        not annee_id
        or not classe_id
        or not affectation_matiere_id
        or not jour
    ):

        return JsonResponse(
            {
                "creneaux": [],
                "error": (
                    "Les informations nécessaires "
                    "ne sont pas encore complètes."
                ),
            }
        )


    try:

        # =================================================
        # VÉRIFICATION DU JOUR
        # =================================================

        jours_valides = [
            choix[0]
            for choix in RepartitionHoraire.JOUR_CHOICES
        ]

        if jour not in jours_valides:

            return JsonResponse(
                {
                    "creneaux": [],
                    "error": (
                        "Le jour sélectionné n'est pas valide."
                    ),
                },
                status=400,
            )


        # =================================================
        # VÉRIFICATION DE LA CLASSE
        # =================================================

        classe = (
            Classe.objects
            .filter(
                id=classe_id,
                annee_id=annee_id,
                actif=True,
            )
            .first()
        )

        if not classe:

            return JsonResponse(
                {
                    "creneaux": [],
                    "error": (
                        "La classe sélectionnée est "
                        "introuvable, inactive ou "
                        "n'appartient pas à cette année."
                    ),
                },
                status=400,
            )


        # =================================================
        # RÉCUPÉRATION DE L'AFFECTATION MATIÈRE
        # =================================================

        affectation_matiere = (
            AffectationMatiere.objects
            .filter(
                id=affectation_matiere_id,
                classe=classe,
                actif=True,
            )
            .select_related(
                "matiere",
                "classe",
            )
            .first()
        )

        if not affectation_matiere:

            return JsonResponse(
                {
                    "creneaux": [],
                    "error": (
                        "La matière sélectionnée n'est pas "
                        "affectée à cette classe ou n'est "
                        "plus active."
                    ),
                },
                status=400,
            )


        # =================================================
        # RECHERCHE DE L'AFFECTATION ENSEIGNANT
        #
        # RepartitionHoraire utilise Affectation.
        # =================================================

        affectation = (
            Affectation.objects
            .filter(
                affectation_matiere=affectation_matiere,
                actif=True,
            )
            .select_related(
                "enseignant",
                "affectation_matiere",
            )
            .first()
        )

        if not affectation:

            return JsonResponse(
                {
                    "creneaux": [],
                    "error": (
                        "Cette matière ne possède pas "
                        "encore d'enseignant actif."
                    ),
                },
                status=400,
            )


        # =================================================
        # VOLUME HORAIRE HEBDOMADAIRE
        # =================================================

        heures_prevues = (
            affectation_matiere.heures_par_semaine
        )

        heures_programmees = (
            RepartitionHoraire.objects
            .filter(
                affectation=affectation,
                actif=True,
            )
            .count()
        )

        heures_restantes = (
            heures_prevues
            - heures_programmees
        )


        # -------------------------------------------------
        # SÉCURITÉ : PAS DE VALEUR NÉGATIVE
        # -------------------------------------------------

        if heures_restantes < 0:

            heures_restantes = 0


        # -------------------------------------------------
        # VOLUME DÉJÀ ATTEINT
        # -------------------------------------------------

        if heures_restantes <= 0:

            return JsonResponse(
                {
                    "creneaux": [],

                    "heures_prevues": (
                        heures_prevues
                    ),

                    "heures_programmees": (
                        heures_programmees
                    ),

                    "heures_restantes": 0,

                    "enseignant": str(
                        affectation.enseignant
                    ),

                    "error": (
                        "Le volume horaire hebdomadaire "
                        "de cette matière est déjà atteint."
                    ),
                }
            )


        # =================================================
        # VÉRIFICATION DE LA CONFIGURATION HORAIRE
        # =================================================

        configuration = (
            ConfigurationHoraire.objects
            .filter(
                annee_id=annee_id,
                verrouillee=True,
            )
            .first()
        )

        if not configuration:

            return JsonResponse(
                {
                    "creneaux": [],

                    "error": (
                        "Aucune configuration horaire "
                        "verrouillée n'existe pour "
                        "cette année scolaire."
                    ),
                },
                status=400,
            )


        # =================================================
        # RÉCUPÉRATION DES CRÉNEAUX DE COURS
        # =================================================

        creneaux = (
            CreneauHoraire.objects
            .filter(
                configuration=configuration,

                type_creneau=(
                    CreneauHoraire.TYPE_COURS
                ),

                actif=True,
            )
            .order_by(
                "ordre"
            )
        )


        # =================================================
        # VÉRIFICATION
        # =================================================

        if not creneaux.exists():

            return JsonResponse(
                {
                    "creneaux": [],

                    "error": (
                        "Aucun créneau de cours actif "
                        "n'existe dans cette configuration."
                    ),
                }
            )


        # =================================================
        # CRÉNEAUX DÉJÀ OCCUPÉS PAR LA CLASSE
        # =================================================

        creneaux_utilises_classe = set(

            RepartitionHoraire.objects
            .filter(
                jour=jour,

                actif=True,

                affectation__affectation_matiere__classe=
                classe,
            )
            .values_list(
                "creneau_id",
                flat=True,
            )

        )


        # =================================================
        # CRÉNEAUX DÉJÀ OCCUPÉS PAR L'ENSEIGNANT
        # =================================================

        creneaux_utilises_enseignant = set(

            RepartitionHoraire.objects
            .filter(
                jour=jour,

                actif=True,

                affectation__enseignant=
                affectation.enseignant,
            )
            .values_list(
                "creneau_id",
                flat=True,
            )

        )


        # =================================================
        # CRÉNEAUX INDISPONIBLES
        # =================================================

        creneaux_indisponibles = (

            creneaux_utilises_classe

            |

            creneaux_utilises_enseignant

        )


        # =================================================
        # CONSTRUCTION DES DONNÉES
        # =================================================

        donnees_creneaux = []


        for creneau in creneaux:

            # ---------------------------------------------
            # CRÉNEAU OCCUPÉ
            # ---------------------------------------------

            if (
                creneau.id
                in creneaux_indisponibles
            ):

                continue


            # ---------------------------------------------
            # CRÉNEAU DISPONIBLE
            # ---------------------------------------------

            donnees_creneaux.append(
                {
                    "id": creneau.id,

                    "numero_heure": (
                        creneau.numero_heure
                    ),

                    "heure_debut": (
                        creneau.heure_debut
                        .strftime("%H:%M")
                    ),

                    "heure_fin": (
                        creneau.heure_fin
                        .strftime("%H:%M")
                    ),

                    "libelle": (
                        f"{creneau.numero_heure}e heure "
                        f"({creneau.heure_debut.strftime('%H:%M')} "
                        f"- "
                        f"{creneau.heure_fin.strftime('%H:%M')})"
                    ),
                }
            )


        # =================================================
        # RÉPONSE JSON
        # =================================================

        return JsonResponse(
            {
                "creneaux": (
                    donnees_creneaux
                ),

                "heures_prevues": (
                    heures_prevues
                ),

                "heures_programmees": (
                    heures_programmees
                ),

                "heures_restantes": (
                    heures_restantes
                ),

                "enseignant": str(
                    affectation.enseignant
                ),

                "affectation_id": (
                    affectation.id
                ),
            }
        )


    # =====================================================
    # GESTION DES ERREURS
    # =====================================================

    except Exception as error:

        return JsonResponse(
            {
                "creneaux": [],

                "error": str(error),
            },
            status=400,
        )

      
def liste_affectations(request):

    # =====================================================
    # RÉCUPÉRATION DES PARAMÈTRES DE FILTRE
    # =====================================================

    annee_id = request.GET.get("annee")
    enseignant_id = request.GET.get("enseignant")
    classe_id = request.GET.get("classe")
    matiere_id = request.GET.get("matiere")


    # =====================================================
    # REQUÊTE PRINCIPALE
    # =====================================================

    affectations = (
        Affectation.objects
        .select_related(
            "enseignant",
            "enseignant__utilisateur",
            "affectation_matiere",
            "affectation_matiere__classe",
            "affectation_matiere__classe__annee",
            "affectation_matiere__matiere",
        )
    )


    # =====================================================
    # FILTRE PAR ANNÉE SCOLAIRE
    # =====================================================

    if annee_id:

        affectations = affectations.filter(
            affectation_matiere__classe__annee_id=annee_id
        )


    # =====================================================
    # FILTRE PAR ENSEIGNANT
    # =====================================================

    if enseignant_id:

        affectations = affectations.filter(
            enseignant_id=enseignant_id
        )


    # =====================================================
    # FILTRE PAR CLASSE
    # =====================================================

    if classe_id:

        affectations = affectations.filter(
            affectation_matiere__classe_id=classe_id
        )


    # =====================================================
    # FILTRE PAR MATIÈRE
    # =====================================================

    if matiere_id:

        affectations = affectations.filter(
            affectation_matiere__matiere_id=matiere_id
        )


    # =====================================================
    # TRI
    # =====================================================

    affectations = affectations.order_by(
        "-affectation_matiere__classe__annee_id",
        "affectation_matiere__classe__libelle",
        "affectation_matiere__matiere__libelle",
        "enseignant__utilisateur__nom",
    )


    # =====================================================
    # DONNÉES DES FILTRES
    # =====================================================

    annees = (
        AnneeScolaire.objects
        .all()
        .order_by("-id")
    )


    enseignants = (
        Enseignant.objects
        .select_related("utilisateur")
        .order_by(
            "utilisateur__nom",
            "utilisateur__prenom",
        )
    )


    classes = (
        Classe.objects
        .all()
        .order_by("libelle")
    )


    matieres = (
        Matiere.objects
        .all()
        .order_by("libelle")
    )


    # =====================================================
    # CONTEXTE
    # =====================================================

    context = {
        "affectations": affectations,
        "annees": annees,
        "enseignants": enseignants,
        "classes": classes,
        "matieres": matieres,
    }


    return render(
        request,
        "enseignant/liste_affectations.html",
        context,
    )

def creer_affectation(request):

    if request.method == "POST":

        form = AffectationForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            message_vers_notification(request, 'SUCCESS', "L'affectation a été créée avec succès.", "L'affectation a été créée avec succès.")

            return redirect(
                "liste_affectations"
            )

    else:

        form = AffectationForm()


    context = {
        "form": form,
    }

    return render(
        request,
        "enseignant/creer_affectation.html",
        context,
    )

def detail_affectation(request, affectation_id):

    affectation = get_object_or_404(
        Affectation.objects.select_related(
            "enseignant",
            "enseignant__utilisateur",
            "affectation_matiere",
            "affectation_matiere__classe",
            "affectation_matiere__classe__annee",
            "affectation_matiere__matiere",
        ),
        id=affectation_id,
    )

    context = {
        "affectation": affectation,
    }

    return render(
        request,
        "enseignant/detail_affectations.html",
        context,
    )

def modifier_affectation(request, affectation_id):

    # =====================================================
    # RÉCUPÉRATION DE L'AFFECTATION
    # =====================================================

    affectation = get_object_or_404(
        Affectation.objects.select_related(
            "enseignant",
            "enseignant__utilisateur",
            "affectation_matiere",
            "affectation_matiere__classe",
            "affectation_matiere__classe__annee",
            "affectation_matiere__matiere",
        ),
        id=affectation_id,
    )


    # =====================================================
    # TRAITEMENT DU FORMULAIRE
    # =====================================================

    if request.method == "POST":

        form = AffectationForm(
            request.POST,
            instance=affectation,
        )

        if form.is_valid():

            form.save()

            message_vers_notification(request, 'SUCCESS', "L'affectation a été modifiée avec succès.", "L'affectation a été modifiée avec succès.")

            return redirect(
                "detail_affectation",
                affectation_id=affectation.id,
            )

    else:

        form = AffectationForm(
            instance=affectation
        )


    # =====================================================
    # CONTEXTE
    # =====================================================

    context = {
        "form": form,
        "affectation": affectation,
    }


    return render(
        request,
        "enseignant/modifier_affectation.html",
        context,
    )

def activer_desactiver_affectation(
    request,
    affectation_id,
):

    affectation = get_object_or_404(
        Affectation.objects.select_related(
            "enseignant",
            "enseignant__utilisateur",
            "affectation_matiere",
            "affectation_matiere__classe",
            "affectation_matiere__classe__annee",
            "affectation_matiere__matiere",
        ),
        id=affectation_id,
    )

    if request.method == "POST":
        if affectation.actif:

            affectation.actif = False

            affectation.save(
                update_fields=["actif"]
            )

            message_vers_notification(request, 'SUCCESS', (
                    "L'affectation a été désactivée "
                    "avec succès."
                ), (
                    "L'affectation a été désactivée "
                    "avec succès."
                ))

        else:

            autre_affectation_active = (
                Affectation.objects.filter(
                    affectation_matiere=(
                        affectation.affectation_matiere
                    ),
                    actif=True,
                )
                .exclude(
                    pk=affectation.pk
                )
                .select_related(
                    "enseignant",
                    "enseignant__utilisateur",
                )
                .first()
            )

            if autre_affectation_active:

                message_vers_notification(request, 'ERROR', (
                        "Impossible d'activer cette "
                        "affectation. La matière "
                        f"« {affectation.affectation_matiere.matiere} » "
                        "est déjà attribuée à un autre "
                        "enseignant pour cette classe et "
                        "cette année scolaire."
                    ), (
                        "Impossible d'activer cette "
                        "affectation. La matière "
                        f"« {affectation.affectation_matiere.matiere} » "
                        "est déjà attribuée à un autre "
                        "enseignant pour cette classe et "
                        "cette année scolaire."
                    ))

                return redirect(
                    "detail_affectation",
                    affectation_id=affectation.id,
                )

            affectation.actif = True

            affectation.save(
                update_fields=["actif"]
            )

            message_vers_notification(request, 'SUCCESS', (
                    "L'affectation a été activée "
                    "avec succès."
                ), (
                    "L'affectation a été activée "
                    "avec succès."
                ))

        return redirect(
            "detail_affectation",
            affectation_id=affectation.id,
        )


    context = {
        "affectation": affectation,
    }

    return render(
        request,
        "enseignant/activer_desactiver_affectations.html",
        context,
    )

def _cle_matiere(libelle):
    """Cle de comparaison insensible aux accents, a la casse et aux espaces.

    Les matieres saisies a la main et celles du programme officiel ne
    portent pas toujours la meme orthographe : "FRANçAIS" et "Français",
    "HISTOIRE" et "Histoire" ou "Algebre" et "Algèbre" designent le meme
    cours. Cette cle permet de rapprocher les deux saisies sans renommer
    ni supprimer aucune matiere.
    """
    decompose = unicodedata.normalize("NFD", libelle or "")

    sans_accents = "".join(
        caractere
        for caractere in decompose
        if unicodedata.category(caractere) != "Mn"
    )

    return " ".join(sans_accents.casefold().split())


def _cours_officiels_de(classe):
    """Ponderations officielles d'une classe, sans doublon de matiere.

    Une matiere peut figurer deux fois dans PonderationMatiere : une
    ligne sans section, identique a la section ELEC, et une ligne propre
    a chaque section. On privilegie la ligne de la section de la classe,
    sinon la ligne sans section.
    """
    if not classe or not classe.niveau_id:
        return []

    par_matiere = {}

    for ponderation in (
        PonderationMatiere.objects
        .filter(niveau=classe.niveau, actif=True)
        .select_related("matiere", "section")
        .order_by("matiere__libelle")
    ):
        if ponderation.section_id and ponderation.section_id != classe.section_id:
            continue

        deja = par_matiere.get(ponderation.matiere_id)

        if deja is None:
            par_matiere[ponderation.matiere_id] = ponderation
        elif ponderation.section_id and not deja.section_id:
            par_matiere[ponderation.matiere_id] = ponderation

    return sorted(
        par_matiere.values(),
        key=lambda ponderation: ponderation.matiere.libelle,
    )


def _lignes_cours_classe(classe):
    """Assemble le programme officiel et l'etat pedagogique de chaque cours.

    Chaque ligne melange ce qui vient de la configuration matiere (le
    cours doit exister) et ce qui a ete saisi (classe, enseignant,
    creneaux). Un cours officiel non encore affecte reste visible avec un
    formulaire d'affectation vide.

    Les deux sources sont fusionnees : une matiere saisie manuellement est
    d'abord recherchee par identifiant, puis par libelle normalise, afin
    qu'un meme cours n'apparaisse pas deux fois. Les matieres saisies
    sans equivalent officiel sont conservees et signalees hors programme :
    elles restent affectables et peuvent recevoir des creneaux.
    """
    affectations_matieres = list(
        AffectationMatiere.objects
        .filter(classe=classe, actif=True)
        .select_related("matiere")
        .order_by("matiere__libelle")
    )

    affectations = {}
    for affectation in (
        Affectation.objects
        .filter(
            affectation_matiere__classe=classe,
            actif=True,
        )
        .select_related("enseignant", "enseignant__utilisateur")
    ):
        affectations.setdefault(
            affectation.affectation_matiere_id,
            affectation,
        )

    repartitions = {}
    for repartition in (
        RepartitionHoraire.objects
        .filter(
            affectation__affectation_matiere__classe=classe,
            actif=True,
        )
        .select_related("creneau")
        .order_by("jour", "creneau__ordre")
    ):
        repartitions.setdefault(
            repartition.affectation_id,
            [],
        ).append(repartition)

    # Index des saisies manuelles, par identifiant puis par cle normalisee.
    par_id = {}
    par_cle = {}

    for affectation_matiere in affectations_matieres:
        par_id[affectation_matiere.matiere_id] = affectation_matiere
        par_cle.setdefault(
            _cle_matiere(affectation_matiere.matiere.libelle),
            affectation_matiere,
        )

    consommes = set()
    lignes = []

    for ponderation in _cours_officiels_de(classe):
        matiere = ponderation.matiere

        affectation_matiere = par_id.get(matiere.id)

        if affectation_matiere is None:
            affectation_matiere = par_cle.get(_cle_matiere(matiere.libelle))

        if affectation_matiere is not None:
            consommes.add(affectation_matiere.id)

        lignes.append({
            "ponderation": ponderation,
            "matiere": matiere,
            "affectation_matiere": affectation_matiere,
            "affectation": (
                affectations.get(affectation_matiere.id)
                if affectation_matiere
                else None
            ),
            "hors_programme": False,
            "repartitions": [],
            "heures_restantes": Decimal("0"),
            "est_affecte": False,
        })

    for affectation_matiere in affectations_matieres:
        if affectation_matiere.id in consommes:
            continue

        lignes.append({
            "ponderation": None,
            "matiere": affectation_matiere.matiere,
            "affectation_matiere": affectation_matiere,
            "affectation": affectations.get(affectation_matiere.id),
            "hors_programme": True,
            "repartitions": [],
            "heures_restantes": Decimal("0"),
            "est_affecte": False,
        })

    for ligne in lignes:
        affectation_matiere = ligne["affectation_matiere"]
        affectation = (
            affectations.get(affectation_matiere.id)
            if affectation_matiere
            else None
        )
        programmees = repartitions.get(affectation.id, []) if affectation else []

        ligne["affectation"] = affectation
        ligne["repartitions"] = programmees
        ligne["est_affecte"] = affectation is not None

        if affectation_matiere:
            volume = Decimal(str(affectation_matiere.heures_par_semaine))
        else:
            volume = Decimal("0")

        placees = sum(
            (
                Decimal(str(_duree_creneau_en_heures(r.creneau)))
                for r in programmees
            ),
            Decimal("0"),
        )

        restantes = volume - placees

        ligne["heures_restantes"] = (
            restantes if restantes > 0 else Decimal("0")
        )

    return sorted(
        lignes,
        key=lambda ligne: (
            ligne["hors_programme"],
            _cle_matiere(ligne["matiere"].libelle),
        ),
    )


@permission_requise("affectation.creer")
def affectation_pedagogique(request):
    """Liaison entre les cours officiels d'une classe et les enseignants.

    La liste des cours provient de PonderationMatiere, donc de la
    configuration matiere : la page presente le programme complet du
    niveau, y compris les matieres encore sans enseignant. Chaque ligne
    permet d'affecter un enseignant, de fixer le volume hebdomadaire,
    puis de placer le cours dans les creneaux de la grille.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    annees = AnneeScolaire.objects.all().order_by("-libelle")

    annee_id = request.GET.get("annee_id") or request.POST.get("annee_id")
    classe_id = request.GET.get("classe_id") or request.POST.get("classe_id")

    annee_selectionnee = None
    if annee_id:
        annee_selectionnee = AnneeScolaire.objects.filter(id=annee_id).first()
    if not annee_selectionnee:
        annee_selectionnee = annee_active

    classes = (
        Classe.objects
        .filter(annee=annee_selectionnee, actif=True)
        .select_related("niveau", "section")
        .order_by("niveau__ordre", "code")
        if annee_selectionnee
        else Classe.objects.none()
    )

    classe = classes.filter(id=classe_id).first() if classe_id else None

    creneaux = (
        CreneauHoraire.objects
        .filter(
            configuration__annee=annee_selectionnee,
            type_creneau=CreneauHoraire.TYPE_COURS,
            actif=True,
        )
        .order_by("ordre")
        if annee_selectionnee
        else CreneauHoraire.objects.none()
    )

    enseignants = (
        Enseignant.objects
        .filter(actif=True, utilisateur__actif=True)
        .select_related("utilisateur")
        .order_by("utilisateur__nom")
    )

    # =========================================================
    # TRAITEMENT DES ACTIONS
    # =========================================================

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "assigner_enseignant":
            return _assigner_enseignant(request)

        if action == "ajouter_creneau":
            return _placer_creneau(request)

        if action == "retirer_creneau":
            return _retirer_creneau(request)

    lignes_cours = _lignes_cours_classe(classe) if classe else []

    volume_total = (
        _volume_total_classe(classe) if classe else Decimal("0")
    )

    # Cours qui depassent le plafond hebdomadaire, a titre
    # d'information : la saisie existante est signalee plutot que
    # silencieusement corrigee.
    cours_hors_plafond = (
        [
            ligne
            for ligne in lignes_cours
            if ligne["affectation_matiere"]
            and (
                Decimal(
                    str(
                        ligne[
                            "affectation_matiere"
                        ].heures_par_semaine
                    )
                )
                > AffectationMatiere.HEURES_MAX_PAR_SEMAINE
                or len(ligne["repartitions"])
                > AffectationMatiere.CRENEAUX_MAX
            )
        ]
        if classe
        else []
    )

    return render(
        request,
        "enseignant/affectation_pedagogique.html",
        {
            "utilisateur": utilisateur,
            "annees": annees,
            "annee_selectionnee": annee_selectionnee,
            "classes": classes,
            "classe": classe,
            "creneaux": creneaux,
            "enseignants": enseignants,
            "jours": RepartitionHoraire.JOUR_CHOICES,
            "cours": lignes_cours,
            "volume_total": volume_total,
            "plafond_cours": AffectationMatiere.HEURES_MAX_PAR_SEMAINE,
            "plafond_creneaux": AffectationMatiere.CRENEAUX_MAX,
            "cours_hors_plafond": cours_hors_plafond,
            "nb_affectes": sum(
                1 for ligne in lignes_cours if ligne["est_affecte"]
            ),
        },
    )


def _url_affectation_pedagogique(annee_id, classe_id):
    return (
        f"{reverse('affectation_pedagogique')}"
        f"?annee_id={annee_id}&classe_id={classe_id}"
    )


def _volume_total_classe(classe, exclude_id=None):
    """Volume hebdomadaire deja saisi pour une classe."""
    lignes = AffectationMatiere.objects.filter(classe=classe, actif=True)

    if exclude_id:
        lignes = lignes.exclude(id=exclude_id)

    return sum(
        (
            Decimal(str(ligne.heures_par_semaine))
            for ligne in lignes
        ),
        Decimal("0"),
    )


def _affectation_matiere_de(classe, matiere, creer=False):
    """Affectation de matiere d'une classe pour une matiere donnee.

    Retourne un couple (ligne, cree). La matiere peut venir du programme
    officiel alors qu'une saisie manuelle equivalente porte un autre
    identifiant : "Algebre" et "Algèbre" designent le meme cours. La
    recherche se fait donc par identifiant, puis par libelle normalise,
    afin de ne jamais creer un doublon pour un cours deja saisi.
    """
    existantes = AffectationMatiere.objects.filter(
        classe=classe,
        actif=True,
    ).select_related("matiere")

    for existante in existantes:
        if existante.matiere_id == matiere.id:
            return existante, False

    cle = _cle_matiere(matiere.libelle)

    for existante in existantes:
        if _cle_matiere(existante.matiere.libelle) == cle:
            return existante, False

    if not creer:
        return None, False

    return AffectationMatiere.objects.create(
        classe=classe,
        matiere=matiere,
        heures_par_semaine=Decimal("1"),
        actif=True,
    ), True


def _assigner_enseignant(request):
    """Cree le lien matiere/classe puis le lien enseignant, au besoin."""
    annee_id = request.POST.get("annee_id")
    classe_id = request.POST.get("classe_id")

    classe = Classe.objects.filter(id=classe_id, actif=True).first()
    matiere = Matiere.objects.filter(id=request.POST.get("matiere_id")).first()
    enseignant = (
        Enseignant.objects
        .filter(id=request.POST.get("enseignant_id"), actif=True)
        .select_related("utilisateur")
        .first()
    )

    if not classe or not matiere or not enseignant:
        message_vers_notification(
            request, "ERROR",
            "Classe, matière ou enseignant introuvable.",
            "Classe, matière ou enseignant introuvable.",
        )
        return redirect(_url_affectation_pedagogique(annee_id, classe_id))

    volume = request.POST.get("heures_par_semaine")

    try:
        volume = int(volume)
        if volume < 1:
            raise ValueError
    except (TypeError, ValueError):
        message_vers_notification(
            request, "ERROR",
            "Le volume horaire hebdomadaire doit être un nombre supérieur à zéro.",
            "Le volume horaire hebdomadaire doit être un nombre supérieur à zéro.",
        )
        return redirect(_url_affectation_pedagogique(annee_id, classe_id))

    # Un cours ne peut pas depasser le plafond hebdomadaire : au-dela
    # c'est une erreur de saisie, et la grille devient illisible.
    if volume > AffectationMatiere.HEURES_MAX_PAR_SEMAINE:
        message_vers_notification(
            request, "ERROR",
            f"« {matiere.libelle} » ne peut pas recevoir "
            f"{volume} h par semaine : le maximum est de "
            f"{AffectationMatiere.HEURES_MAX_PAR_SEMAINE} h par "
            f"cours et par semaine.",
            f"« {matiere.libelle} » ne peut pas recevoir "
            f"{volume} h par semaine : le maximum est de "
            f"{AffectationMatiere.HEURES_MAX_PAR_SEMAINE} h par "
            f"cours et par semaine.",
        )
        return redirect(_url_affectation_pedagogique(annee_id, classe_id))

    try:
        with transaction.atomic():
            # La matiere du formulaire peut porter l'identifiant officiel
            # alors qu'une saisie manuelle equivalente existe deja sous un
            # autre identifiant. On la recherche avant de creer, sinon la
            # classe se retrouve avec deux lignes pour le meme cours.
            affectation_matiere, cree = _affectation_matiere_de(
                classe,
                matiere,
                creer=True,
            )

            if not cree and (
                affectation_matiere.heures_par_semaine != volume
            ):
                affectation_matiere.heures_par_semaine = volume
                affectation_matiere.save(
                    update_fields=["heures_par_semaine"]
                )

            if cree:
                message_vers_notification(
                    request, "SUCCESS",
                    f"La matière « {matiere.libelle} » a été ajoutée "
                    f"à la classe « {classe.libelle} ».",
                    f"La matière « {matiere.libelle} » a été ajoutée "
                    f"à la classe « {classe.libelle} ».",
                )

            affectation, cree_affectation = Affectation.objects.get_or_create(
                enseignant=enseignant,
                affectation_matiere=affectation_matiere,
                defaults={"actif": True},
            )

            if cree_affectation:
                message_vers_notification(
                    request, "SUCCESS",
                    f"{enseignant} assure désormais « {matiere.libelle} » "
                    f"en {classe.libelle}.",
                    f"{enseignant} assure désormais « {matiere.libelle} » "
                    f"en {classe.libelle}.",
                )

            # Un changement d'enseignant passe par la desactivation de
            # l'ancienne affectation plutot que par sa suppression.
            for autre in Affectation.objects.filter(
                affectation_matiere=affectation_matiere,
                actif=True,
            ).exclude(id=affectation.id):
                autre.actif = False
                autre.save(update_fields=["actif"])

    except ValidationError as erreur:
        message_vers_notification(
            request, "ERROR",
            " ; ".join(
                " ".join(str(valeur) for valeur in valeurs)
                for valeurs in erreur.message_dict.values()
            )[:200],
            "Affectation refusée par les règles de l'établissement.",
        )
    except IntegrityError:
        message_vers_notification(
            request, "ERROR",
            "Cet enseignant est déjà affecté à cette matière dans cette classe.",
            "Cet enseignant est déjà affecté à cette matière dans cette classe.",
        )

    return redirect(_url_affectation_pedagogique(annee_id, classe_id))


def _placer_creneau(request):
    """Place un cours affecte dans un creneau de la grille."""
    annee_id = request.POST.get("annee_id")
    classe_id = request.POST.get("classe_id")

    affectation = Affectation.objects.filter(
        id=request.POST.get("affectation_id"),
        actif=True,
        affectation_matiere__classe_id=classe_id,
    ).first()

    jour = request.POST.get("jour")
    creneau_id = request.POST.get("creneau_id")

    if not affectation or not jour or not creneau_id:
        message_vers_notification(
            request, "ERROR",
            "Cours, jour ou créneau manquant.",
            "Cours, jour ou créneau manquant.",
        )
        return redirect(_url_affectation_pedagogique(annee_id, classe_id))

    repartition = RepartitionHoraire(
        affectation=affectation,
        jour=jour,
        creneau_id=creneau_id,
    )

    try:
        repartition.full_clean()
        repartition.save()
        message_vers_notification(
            request, "SUCCESS",
            "Le cours a été placé dans la grille horaire.",
            "Le cours a été placé dans la grille horaire.",
        )
    except ValidationError as erreur:
        message_vers_notification(
            request, "ERROR",
            " ; ".join(
                " ".join(str(valeur) for valeur in valeurs)
                for valeurs in erreur.message_dict.values()
            )[:200],
            "Créneau refusé pour ce cours.",
        )
    except (IntegrityError, ValueError, TypeError):
        message_vers_notification(
            request, "ERROR",
            "Ce cours est déjà placé dans ce créneau.",
            "Ce cours est déjà placé dans ce créneau.",
        )

    return redirect(_url_affectation_pedagogique(annee_id, classe_id))


def _retirer_creneau(request):
    annee_id = request.POST.get("annee_id")
    classe_id = request.POST.get("classe_id")

    repartition = RepartitionHoraire.objects.filter(
        id=request.POST.get("repartition_id"),
        actif=True,
        affectation__affectation_matiere__classe_id=classe_id,
    ).first()

    if not repartition:
        message_vers_notification(
            request, "ERROR",
            "Créneau introuvable.",
            "Créneau introuvable.",
        )
        return redirect(_url_affectation_pedagogique(annee_id, classe_id))

    repartition.delete()

    message_vers_notification(
        request, "SUCCESS",
        "Le cours a été retiré de la grille horaire.",
        "Le cours a été retiré de la grille horaire.",
    )

    return redirect(_url_affectation_pedagogique(annee_id, classe_id))


def interface_enseignants(request):

    total_enseignants = (
        Enseignant.objects.count()
    )

    enseignants_actifs = (
        Enseignant.objects.filter(
            actif=True,
            utilisateur__actif=True,
        ).count()
    )


    enseignants_inactifs = (
        Enseignant.objects.filter(
            actif=False
        ).count()
    )


    # =====================================================
    # ENSEIGNANTS AYANT AU MOINS UNE AFFECTATION ACTIVE
    # =====================================================

    enseignants_affectes = (
        Enseignant.objects.filter(
            affectations__actif=True
        )
        .distinct()
        .count()
    )


    # =====================================================
    # ENSEIGNANTS ACTIFS SANS AFFECTATION ACTIVE
    # =====================================================

    enseignants_sans_affectation = (
        Enseignant.objects.filter(
            actif=True,
            utilisateur__actif=True,
        )
        .exclude(
            affectations__actif=True
        )
        .distinct()
        .count()
    )


    # =====================================================
    # DERNIÈRES AFFECTATIONS
    # =====================================================

    dernieres_affectations = (
        Affectation.objects.select_related(
            "enseignant__utilisateur",
            "affectation_matiere__matiere",
            "affectation_matiere__classe",
        )
        .order_by(
            "-id"
        )[:5]
    )


    # =====================================================
    # AFFICHAGE DE LA PAGE
    # =====================================================

    return render(
        request,
        "enseignant/interface_enseignants.html",
        {
            "total_enseignants": total_enseignants,
            "enseignants_actifs": enseignants_actifs,
            "enseignants_inactifs": enseignants_inactifs,
            "enseignants_affectes": enseignants_affectes,
            "enseignants_sans_affectation": (
                enseignants_sans_affectation
            ),
            "dernieres_affectations": (
                dernieres_affectations
            ),
        }
    )

# ============================================================
# TITULARISATION - ASSIGNER UN ENSEIGNANT COMME TITULAIRE DE CLASSE
# ============================================================

import logging
logger = logging.getLogger(__name__)

@permission_requise("TITULARISATION_CREER")
def creer_titularisation(request):
    """
    Vue pour permettre au directeur d'assigner un enseignant comme titulaire de classe.
    """
    if request.method == "POST":
        form = TitularisationForm(request.POST)
        logger.debug(f"POST data: {request.POST}")
        logger.debug(f"Form is valid: {form.is_valid()}")
        if not form.is_valid():
            logger.debug(f"Form errors: {form.errors}")
        if form.is_valid():
            try:
                with transaction.atomic():
                    titularisation = form.save()
                    
                    message_vers_notification(request, 'SUCCESS', 
                        f"L'enseignant {titularisation.enseignant.utilisateur.prenom} {titularisation.enseignant.utilisateur.nom} "
                        f"a été assigné comme titulaire de la classe {titularisation.classe.libelle} "
                        f"pour l'année {titularisation.annee.libelle}.",
                        f"L'enseignant {titularisation.enseignant.utilisateur.prenom} {titularisation.enseignant.utilisateur.nom} "
                        f"a été assigné comme titulaire de la classe {titularisation.classe.libelle} "
                        f"pour l'année {titularisation.annee.libelle}."
                    )
                    
                    enregistrer_historique(
                        request=request,
                        code_action="TITULARISATION_CREATION",
                        table_cible="titularisation",
                        id_cible=titularisation.id,
                        nouvelle_valeur=(
                            f"Titularisation créée : "
                            f"{titularisation.enseignant} - "
                            f"{titularisation.classe} - {titularisation.annee}"
                        ),
                        motif="Assignation d'un enseignant comme titulaire de classe."
                    )
                    
                    return redirect("dashboard_directeur")
            except ValidationError as e:
                logger.error(f"ValidationError: {e}")
                message_vers_notification(request, 'ERROR', str(e), str(e))
            except Exception as e:
                logger.exception(f"Error creating titularisation: {e}")
                message_vers_notification(request, 'ERROR', 
                    f"Une erreur est survenue lors de la création de la titularisation : {e}",
                    f"Une erreur est survenue lors de la création de la titularisation : {e}"
                )
    else:
        form = TitularisationForm()

    return render(
        request,
        "enseignant/creer_titularisation.html",
        {
            "form": form,
        }
    )


# ============================================================
# AJAX - OPTIONS DE TITULARISATION POUR UNE ANNÉE SCOLAIRE
# ============================================================

@permission_requise("TITULARISATION_CREER")
def ajax_options_titularisation(request):
    """
    Renvoie les classes et les enseignants qui peuvent encore
    être associés comme titulaires pour une année scolaire.

    Les classes déjà pourvues d'un titulaire actif et les
    enseignants déjà titulaires d'une classe sont exclus.
    """

    annee_id = request.GET.get("annee_id")

    if not annee_id:
        return JsonResponse(
            {
                "classes": [],
                "enseignants": [],
            }
        )

    try:

        annee_id = int(annee_id)

    except (TypeError, ValueError):

        return JsonResponse(
            {
                "classes": [],
                "enseignants": [],
                "error": "Année scolaire invalide.",
            },
            status=400,
        )

    try:

        # --------------------------------------------------------
        # TITULARISATIONS DÉJÀ ACTIVES
        # --------------------------------------------------------

        titularisations_actives = Titularisation.objects.filter(
            annee_id=annee_id,
            statut=Titularisation.ACTIVE,
        )

        classes_titulaires = titularisations_actives.values_list(
            "classe_id",
            flat=True,
        )

        enseignants_titulaires = titularisations_actives.values_list(
            "enseignant_id",
            flat=True,
        )

        # --------------------------------------------------------
        # CLASSES DISPONIBLES
        # --------------------------------------------------------

        classes_disponibles = (
            Classe.objects
            .filter(
                annee_id=annee_id,
                actif=True,
            )
            .exclude(id__in=classes_titulaires)
            .select_related("niveau", "section")
            .order_by("niveau__ordre", "code")
        )

        donnees_classes = [
            {
                "id": classe.id,
                "code": classe.code,
                "libelle": classe.libelle,
                "niveau": (
                    classe.niveau.libelle
                    if classe.niveau_id else ""
                ),
            }
            for classe in classes_disponibles
        ]

        # --------------------------------------------------------
        # ENSEIGNANTS DISPONIBLES
        # --------------------------------------------------------

        enseignants_disponibles = (
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

        donnees_enseignants = [
            {
                "id": enseignant.id,
                "matricule": enseignant.matricule,
                "nom": (
                    f"{enseignant.utilisateur.nom} "
                    f"{enseignant.utilisateur.prenom}"
                ).strip(),
                "grade": enseignant.grade,
            }
            for enseignant in enseignants_disponibles
        ]

        return JsonResponse(
            {
                "classes": donnees_classes,
                "enseignants": donnees_enseignants,
            }
        )

    except Exception as error:

        return JsonResponse(
            {
                "classes": [],
                "enseignants": [],
                "error": str(error),
            },
            status=400,
        )


# ============================================================
# MA CLASSE - VUE POUR L'ENSEIGNANT TITULAIRE
# ============================================================

@role_requis("ENSEIGNANT")
def ma_classe(request):
    """
    Vue pour permettre à l'enseignant titulaire de voir les informations de sa classe :
    - Liste des élèves
    - Cours (matières affectées)
    - Résultats des points par périodes
    """
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return redirect("connexion")
    
    # Récupérer l'enseignant associé à l'utilisateur
    try:
        enseignant = Enseignant.objects.get(utilisateur=utilisateur, actif=True)
    except Enseignant.DoesNotExist:
        message_vers_notification(request, 'ERROR', "Vous n'êtes pas associé à un profil enseignant.", "Vous n'êtes pas associé à un profil enseignant.")
        return redirect("dashboard_enseignant")
    
    # Récupérer la classe dont l'enseignant est titulaire (année active)
    annee_active = AnneeScolaire.objects.filter(statut=AnneeScolaire.ACTIVE).first()
    
    if not annee_active:
        message_vers_notification(request, 'WARNING', "Aucune année scolaire active trouvée.", "Aucune année scolaire active trouvée.")
        return render(request, "enseignant/ma_classe.html", {
            "utilisateur": utilisateur,
            "enseignant": enseignant,
            "classe": None,
            "eleves": [],
            "matieres": [],
            "resultats_par_periode": {},
        })
    
    titularisation = Titularisation.objects.filter(
        enseignant=enseignant,
        annee=annee_active,
        statut=Titularisation.ACTIVE,
    ).select_related("classe", "classe__niveau", "classe__section", "annee").first()
    
    if not titularisation:
        message_vers_notification(request, 'INFO', "Vous n'êtes pas titulaire d'une classe pour l'année active.", "Vous n'êtes pas titulaire d'une classe pour l'année active.")
        return render(request, "enseignant/ma_classe.html", {
            "utilisateur": utilisateur,
            "enseignant": enseignant,
            "classe": None,
            "eleves": [],
            "matieres": [],
            "resultats_par_periode": {},
        })
    
    classe = titularisation.classe
    
    # Récupérer les élèves de la classe
    inscriptions = Inscription.objects.filter(
        classe=classe,
        annee=annee_active,
        statut=Inscription.ACTIVE,
    ).select_related("eleve").order_by("eleve__nom", "eleve__prenom")
    
    eleves = [inscription.eleve for inscription in inscriptions]
    
    # Récupérer les matières affectées à la classe
    affectations_matieres = AffectationMatiere.objects.filter(
        classe=classe,
        actif=True,
    ).select_related("matiere", "matiere__domaine").order_by("matiere__domaine__ordre", "matiere__libelle")
    
    matieres = [am.matiere for am in affectations_matieres]
    
    # Récupérer les périodes de l'année active
    semestres = Semestre.objects.filter(annee=annee_active).order_by("numero")
    periodes = Periode.objects.filter(semestre__in=semestres).order_by("semestre__numero", "numero")
    
    # Récupérer les résultats par période pour chaque élève
    resultats_par_periode = {}
    for periode in periodes:
        resultats = ResultatPeriode.objects.filter(
            periode=periode,
            inscription__classe=classe,
            inscription__annee=annee_active,
        ).select_related("inscription", "inscription__eleve").order_by("inscription__eleve__nom", "inscription__eleve__prenom")
        
        resultats_par_periode[periode] = {
            resultat.inscription.eleve_id: resultat for resultat in resultats
        }
    
    return render(request, "enseignant/ma_classe.html", {
        "utilisateur": utilisateur,
        "enseignant": enseignant,
        "classe": classe,
        "eleves": eleves,
        "matieres": matieres,
        "periodes": periodes,
        "resultats_par_periode": resultats_par_periode,
        "annee_active": annee_active,
    })


# =========================================================
# INTERFACE ORGANISATION SCOLAIRE
# =========================================================

def interface_organisation_scolaire(request):

    return render(
        request,
        "organisation/interface_organisation_scolaire.html"
    )
    
# =============================================================
# CONFIGURATION DE LA JOURNÉE
# =============================================================

def configuration_journee(request):
    annee_id = request.GET.get("annee_id")

    annee_selectionnee = None
    configuration = None
    creneaux = CreneauHoraire.objects.none()

    # =========================================================
    # ANNÉE SÉLECTIONNÉE
    # =========================================================

    if annee_id:
        annee_selectionnee = get_object_or_404(
            AnneeScolaire,
            id=annee_id
        )

        configuration = (
            ConfigurationHoraire.objects
            .filter(annee=annee_selectionnee)
            .first()
        )

        # -----------------------------------------------------
        # CRÉNEAUX DE LA CONFIGURATION
        # -----------------------------------------------------

        if configuration:
            creneaux = (
                CreneauHoraire.objects
                .filter(
                    configuration=configuration,
                    actif=True
                )
                .order_by("ordre")
            )

    # =========================================================
    # ENREGISTREMENT DE LA CONFIGURATION
    # =========================================================

    if request.method == "POST":

        # -----------------------------------------------------
        # CONFIGURATION EXISTANTE
        # -----------------------------------------------------

        if configuration:

            if configuration.verrouillee:
                message_vers_notification(request, 'ERROR', (
                        "Cette configuration horaire est "
                        "verrouillée et ne peut plus être modifiée."
                    ), (
                        "Cette configuration horaire est "
                        "verrouillée et ne peut plus être modifiée."
                    ))

                return redirect(
                    "configuration_journee"
                    
                )

            form = ConfigurationHoraireForm(
                request.POST,
                instance=configuration
            )

        # -----------------------------------------------------
        # NOUVELLE CONFIGURATION
        # -----------------------------------------------------

        else:
            form = ConfigurationHoraireForm(
                request.POST
                
            )

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if form.is_valid():

            configuration = form.save()

            message_vers_notification(request, 'SUCCESS', (
                    "La configuration de la journée scolaire "
                    "a été enregistrée avec succès."
                ), (
                    "La configuration de la journée scolaire "
                    "a été enregistrée avec succès."
                ))

            return redirect(
                f"{reverse('configuration_journee')}?annee_id={configuration.annee.id}"
            )

    # =========================================================
    # AFFICHAGE INITIAL
    # =========================================================

    else:

        if configuration:

            form = ConfigurationHoraireForm(
                instance=configuration
            )

        else:

            initial = {}

            if annee_selectionnee:
                initial["annee"] = annee_selectionnee

            form = ConfigurationHoraireForm(
                initial=initial
            )

    # =========================================================
    # ANNÉES SCOLAIRES
    # =========================================================

    annees = (
        AnneeScolaire.objects
        .all()
        .order_by("-id")
    )

    # =========================================================
    # AFFICHAGE
    # =========================================================

    return render(
        request,
        "organisation/configuration_journee.html",
        {
            "form": form,
            "annees": annees,
            "annee_selectionnee": annee_selectionnee,
            "configuration": configuration,
            "creneaux": creneaux,
        }
    )


# =============================================================
# GÉNÉRATION DES CRÉNEAUX
# =============================================================

@transaction.atomic
def generer_creneaux(request, configuration_id):

    configuration = get_object_or_404(
        ConfigurationHoraire,
        id=configuration_id
    )

    # =========================================================
    # POST UNIQUEMENT
    # =========================================================

    if request.method != "POST":
        message_vers_notification(request, 'ERROR', "Cette opération n'est pas autorisée.", "Cette opération n'est pas autorisée.")

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # CONFIGURATION VERROUILLÉE
    # =========================================================

    if configuration.verrouillee:

        message_vers_notification(request, 'ERROR', (
                "Cette configuration est verrouillée. "
                "Les créneaux ne peuvent plus être générés."
            ), (
                "Cette configuration est verrouillée. "
                "Les créneaux ne peuvent plus être générés."
            ))

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # VALIDATION DE LA CONFIGURATION
    # =========================================================

    try:
        configuration.full_clean()

    except ValidationError as e:

        message_vers_notification(request, 'ERROR', (
                "Impossible de générer les créneaux. "
                "La configuration est invalide."
            ), (
                "Impossible de générer les créneaux. "
                "La configuration est invalide."
            ))

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # SUPPRESSION DES ANCIENS CRÉNEAUX
    #
    # Possible uniquement parce que la configuration
    # n'est pas encore verrouillée.
    #
    # Les creneaux restent utilises par Horaire et RepartitionHoraire :
    # on ne peut donc pas les supprimer tant que des cours sont
    # deja places. Dans ce cas on explique quoi faire, plutot que de
    # renvoyer une erreur 500.
    # =========================================================

    creneaux_a_supprimer = CreneauHoraire.objects.filter(
        configuration=configuration
    )

    horaires_lies = Horaire.objects.filter(
        creneau__configuration=configuration
    ).count()

    repartitions_liees = RepartitionHoraire.objects.filter(
        creneau__configuration=configuration
    ).count()

    if horaires_lies or repartitions_liees:

        details = []

        if horaires_lies:
            details.append(
                f"{horaires_lies} place(s) dans l'emploi du temps"
            )

        if repartitions_liees:
            details.append(
                f"{repartitions_liees} repartition(s) horaire(s)"
            )

        message_vers_notification(request, 'ERROR', (
                "Impossible de generer les creneaux : des cours sont "
                "deja places sur les creneaux actuels ("
                + " ; ".join(details)
                + "). Supprimez d'abord ces cours, puis relancez la "
                "generation des creneaux."
            ), (
                "Impossible de generer les creneaux : des cours sont "
                "deja places sur les creneaux actuels ("
                + " ; ".join(details)
                + "). Supprimez d'abord ces cours, puis relancez la "
                "generation des creneaux."
            ))

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    creneaux_a_supprimer.delete()

    # =========================================================
    # PARAMÈTRES
    # =========================================================

    heure_debut = configuration.heure_debut_journee
    duree_heure = configuration.duree_heure
    nombre_heures = configuration.nombre_heures_par_jour
    pause_apres = configuration.pause_apres_heure
    duree_pause = configuration.duree_pause

    # =========================================================
    # HEURE DE DÉPART
    # =========================================================

    date_reference = datetime.combine(
        datetime.today().date(),
        heure_debut
    )

    heure_actuelle = date_reference

    creneaux = []

    ordre = 1

    # =========================================================
    # GÉNÉRATION
    # =========================================================

    for numero_heure in range(
        1,
        nombre_heures + 1
    ):

        # -----------------------------------------------------
        # DÉBUT
        # -----------------------------------------------------

        debut = heure_actuelle

        # -----------------------------------------------------
        # FIN
        # -----------------------------------------------------

        fin = (
            debut
            + timedelta(
                minutes=duree_heure
            )
        )

        # -----------------------------------------------------
        # COURS
        # -----------------------------------------------------

        creneaux.append(
            CreneauHoraire(
                configuration=configuration,
                ordre=ordre,
                type_creneau=CreneauHoraire.TYPE_COURS,
                numero_heure=numero_heure,
                heure_debut=debut.time(),
                heure_fin=fin.time(),
                actif=True,
            )
        )

        ordre += 1

        heure_actuelle = fin

        # -----------------------------------------------------
        # PAUSE
        # -----------------------------------------------------

        if (
            numero_heure == pause_apres
            and numero_heure < nombre_heures
        ):

            debut_pause = heure_actuelle

            fin_pause = (
                debut_pause
                + timedelta(
                    minutes=duree_pause
                )
            )

            creneaux.append(
                CreneauHoraire(
                    configuration=configuration,
                    ordre=ordre,
                    type_creneau=CreneauHoraire.TYPE_PAUSE,
                    numero_heure=None,
                    heure_debut=debut_pause.time(),
                    heure_fin=fin_pause.time(),
                    actif=True,
                )
            )

            ordre += 1

            heure_actuelle = fin_pause

    # =========================================================
    # ENREGISTREMENT
    # =========================================================

    CreneauHoraire.objects.bulk_create(
        creneaux
    )

    # =========================================================
    # MESSAGE
    # =========================================================

    message_vers_notification(request, 'SUCCESS', (
            f"{len(creneaux)} créneaux ont été générés "
            "avec succès."
        ), (
            f"{len(creneaux)} créneaux ont été générés "
            "avec succès."
        ))

    return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )


# =============================================================
# VALIDATION ET VERROUILLAGE DÉFINITIF
# =============================================================

@transaction.atomic
def valider_configuration_horaire(
    request,
    configuration_id
):

    configuration = get_object_or_404(
        ConfigurationHoraire,
        id=configuration_id
    )

    # =========================================================
    # POST UNIQUEMENT
    # =========================================================

    if request.method != "POST":

        message_vers_notification(request, 'ERROR', "Cette opération n'est pas autorisée.", "Cette opération n'est pas autorisée.")

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # DÉJÀ VERROUILLÉE
    # =========================================================

    if configuration.verrouillee:

        message_vers_notification(request, 'WARNING', "Cette configuration est déjà verrouillée.", "Cette configuration est déjà verrouillée.")

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # VALIDATION DE LA CONFIGURATION
    # =========================================================

    try:
        configuration.full_clean()

    except ValidationError:

        message_vers_notification(request, 'ERROR', (
                "La configuration est invalide. "
                "Elle ne peut pas être verrouillée."
            ), (
                "La configuration est invalide. "
                "Elle ne peut pas être verrouillée."
            ))

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # RÉCUPÉRATION DES CRÉNEAUX
    # =========================================================

    creneaux = CreneauHoraire.objects.filter(
        configuration=configuration,
        actif=True
    ).order_by("ordre")

    # =========================================================
    # CONTRÔLE : DES CRÉNEAUX EXISTENT-ILS ?
    # =========================================================

    if not creneaux.exists():

        message_vers_notification(request, 'ERROR', (
                "Impossible de verrouiller la configuration "
                "car aucun créneau n'a été généré."
            ), (
                "Impossible de verrouiller la configuration "
                "car aucun créneau n'a été généré."
            ))

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # CONTRÔLE DU NOMBRE DE CRÉNEAUX DE COURS
    # =========================================================

    nombre_creneaux_cours = creneaux.filter(
        type_creneau=CreneauHoraire.TYPE_COURS
    ).count()

    if (
        nombre_creneaux_cours
        != configuration.nombre_heures_par_jour
    ):

        message_vers_notification(request, 'ERROR', (
                "Le nombre de créneaux de cours générés "
                "ne correspond pas à la configuration."
            ), (
                "Le nombre de créneaux de cours générés "
                "ne correspond pas à la configuration."
            ))

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # CONTRÔLE DE LA PAUSE
    # =========================================================

    nombre_pauses = creneaux.filter(
        type_creneau=CreneauHoraire.TYPE_PAUSE
    ).count()

    if nombre_pauses != 1:

        message_vers_notification(request, 'ERROR', (
                "La configuration doit contenir exactement "
                "une pause."
            ), (
                "La configuration doit contenir exactement "
                "une pause."
            ))

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )

    # =========================================================
    # VERROUILLAGE DÉFINITIF
    # =========================================================

    configuration.verrouillee = True

    configuration.save(
        update_fields=[
            "verrouillee",
            "date_modification",
        ]
    )

    message_vers_notification(request, 'SUCCESS', (
            "La configuration horaire a été validée "
            "et verrouillée définitivement."
        ), (
            "La configuration horaire a été validée "
            "et verrouillée définitivement."
        ))

    return redirect(
            f"{reverse('configuration_journee')}?annee_id={configuration.annee_id}"
        )
     
def repartition_horaire(request):
    annee_id = request.GET.get("annee_id")
    classe_id = request.GET.get("classe_id")

    annee_selectionnee = None
    classe_selectionnee = None
    creneaux = CreneauHoraire.objects.none()

    if annee_id:
        annee_selectionnee = get_object_or_404(
            AnneeScolaire,
            id=annee_id
        )

        # Vérifier que la configuration existe
        configuration = (
            ConfigurationHoraire.objects.filter(
                annee=annee_selectionnee
            ).first()
        )

        if configuration:
            creneaux = (
                CreneauHoraire.objects.filter(
                    configuration=configuration,
                    type_creneau=CreneauHoraire.TYPE_COURS,
                    actif=True,
                )
                .order_by("ordre")
            )

    if classe_id and annee_selectionnee:
        classe_selectionnee = get_object_or_404(
            Classe,
            id=classe_id,
            annee=annee_selectionnee,
            actif=True,
        )

    classes = Classe.objects.filter(
        annee=annee_selectionnee,
        actif=True,
    ) if annee_selectionnee else Classe.objects.none()

    annees = AnneeScolaire.objects.all()

    # ---------------------------------------------------------
    # Cours déjà placés dans la grille de la classe sélectionnée
    # Indexés par (jour, creneau_id) pour un accès direct au rendu.
    #
    # Deux tables décrivent une occupation de grille :
    #   - RepartitionHoraire, produite par la programmation des cours
    #     et lue par la pop-up d'horaire ;
    #   - Horaire, produite par le bouton « + » de cette page.
    #
    # Elles sont lues toutes les deux, la programmation primant, afin
    # que la grille reflète ce qui est réellement saisi quelle que
    # soit l'origine du cours.
    # ---------------------------------------------------------
    JOURS_NUMERO = {
        RepartitionHoraire.LUNDI: 1,
        RepartitionHoraire.MARDI: 2,
        RepartitionHoraire.MERCREDI: 3,
        RepartitionHoraire.JEUDI: 4,
        RepartitionHoraire.VENDREDI: 5,
        RepartitionHoraire.SAMEDI: 6,
    }

    horaires = {}

    if annee_selectionnee and classe_selectionnee:

        for repartition in (
            RepartitionHoraire.objects
            .filter(
                affectation__affectation_matiere__classe=classe_selectionnee,
                actif=True,
                creneau__configuration__annee=annee_selectionnee,
            )
            .select_related(
                "creneau",
                "affectation",
                "affectation__enseignant",
                "affectation__affectation_matiere",
                "affectation__affectation_matiere__matiere",
            )
        ):
            jour = JOURS_NUMERO.get(repartition.jour)
            if not jour:
                continue

            repartition.table_source = "repartition"
            horaires.setdefault((jour, repartition.creneau_id), repartition)

        for horaire in (
            Horaire.objects
            .filter(
                annee=annee_selectionnee,
                classe=classe_selectionnee,
                actif=True,
            )
            .select_related(
                "creneau",
                "affectation",
                "affectation__enseignant",
                "affectation__affectation_matiere",
                "affectation__affectation_matiere__matiere",
            )
        ):
            horaire.table_source = "horaire"
            horaires.setdefault((horaire.jour_semaine, horaire.creneau_id), horaire)

    return render(
        request,
        "organisation/repartition_horaire.html",
        {
            "annees": annees,
            "classes": classes,
            "annee_selectionnee": annee_selectionnee,
            "classe_selectionnee": classe_selectionnee,
            "creneaux": creneaux,
            "horaires": horaires,
        }
    )

def affecter_cours(request, annee_id, classe_id, creneau_id, jour):

    # =========================================================
    # RÉCUPÉRATION DES OBJETS
    # =========================================================

    annee = get_object_or_404(
        AnneeScolaire,
        id=annee_id
    )

    classe = get_object_or_404(
        Classe,
        id=classe_id,
        annee=annee
    )

    creneau = get_object_or_404(
        CreneauHoraire,
        id=creneau_id,
        configuration__annee=annee
    )

    # =========================================================
    # VÉRIFICATION DU JOUR
    # =========================================================

    if jour < 1 or jour > 6:

        message_vers_notification(request, 'ERROR', "Le jour sélectionné est invalide.", "Le jour sélectionné est invalide.")

        return redirect(
            f"{reverse('repartition_horaire')}?annee_id={annee.id}"
        )

    # =========================================================
    # LA PAUSE NE PEUT PAS RECEVOIR DE COURS
    # =========================================================

    if creneau.type_creneau == CreneauHoraire.TYPE_PAUSE:

        message_vers_notification(request, 'ERROR', "Impossible d'affecter un cours pendant la pause.", "Impossible d'affecter un cours pendant la pause.")

        return redirect(
            f"{reverse('repartition_horaire')}?annee_id={annee.id}"
        )

    # =========================================================
    # CONFIGURATION DOIT ÊTRE VERROUILLÉE
    # =========================================================

    configuration = creneau.configuration

    if not configuration.verrouillee:

        message_vers_notification(request, 'ERROR', (
                "La configuration horaire doit être "
                "validée et verrouillée avant de répartir "
                "les cours."
            ), (
                "La configuration horaire doit être "
                "validée et verrouillée avant de répartir "
                "les cours."
            ))

        return redirect(
            f"{reverse('configuration_journee')}?annee_id={annee.id}"
        )

    # =========================================================
    # CRÉNEAU ACTIF
    # =========================================================

    if not creneau.actif:

        message_vers_notification(request, 'ERROR', "Ce créneau horaire est inactif.", "Ce créneau horaire est inactif.")

        return redirect(
            f"{reverse('repartition_horaire')}?annee_id={annee.id}"
        )

    # =========================================================
    # LA CLASSE EST-ELLE DÉJÀ OCCUPÉE ?
    # =========================================================

    horaire_existant = Horaire.objects.filter(
        annee=annee,
        classe=classe,
        jour_semaine=jour,
        creneau=creneau,
        actif=True,
    ).exists()

    if horaire_existant:

        message_vers_notification(request, 'WARNING', (
                "Cette classe possède déjà un cours "
                "à ce créneau."
            ), (
                "Cette classe possède déjà un cours "
                "à ce créneau."
            ))

        return redirect(
            f"{reverse('repartition_horaire')}?annee_id={annee.id}"
        )

    # =========================================================
    # FORMULAIRE
    # =========================================================

    if request.method == "POST":

        form = HoraireForm(
            request.POST,
            annee=annee,
            classe=classe,
            creneau=creneau,
            jour_semaine=jour,
        )

        if form.is_valid():

            horaire = form.save()

            message_vers_notification(request, 'SUCCESS', "Le cours a été affecté avec succès à la classe.", "Le cours a été affecté avec succès à la classe.")

            return redirect(
                f"{reverse('repartition_horaire')}"
                f"?annee_id={annee.id}&classe_id={classe.id}"
            )

    else:

        form = HoraireForm(
            annee=annee,
            classe=classe,
            creneau=creneau,
            jour_semaine=jour,
        )

    # =========================================================
    # AFFICHAGE
    # =========================================================

    return render(
        request,
        "organisation/affecter_cours.html",
        {
            "form": form,
            "annee": annee,
            "classe": classe,
            "creneau": creneau,
            "jour": jour,
        }
    )

def supprimer_horaire(request, horaire_id):
    """Retire un cours place dans la grille jour x créneau.

    La grille affiche des cours issus de deux tables. `?source=` designe
    celle du cours a supprimer ; par defaut l'ancienne table Horaire,
    qui reste la cible du bouton « + » de cette page.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    source = (
        request.POST.get("source")
        or request.GET.get("source")
        or "horaire"
    )

    if request.method != "POST":
        message_vers_notification(
            request,
            "ERROR",
            "Cette opération n'est pas autorisée.",
            "Cette opération n'est pas autorisée.",
        )
        return redirect("repartition_horaire")

    if source == "repartition":
        occupation = get_object_or_404(
            RepartitionHoraire.objects.select_related(
                "affectation__affectation_matiere__classe",
            ),
            id=horaire_id,
        )
        classe = occupation.affectation.affectation_matiere.classe
    else:
        occupation = get_object_or_404(
            Horaire.objects.select_related("annee", "classe", "creneau"),
            id=horaire_id,
        )
        classe = occupation.classe

    occupation.delete()

    message_vers_notification(
        request,
        "SUCCESS",
        "Le cours a été retiré de l'emploi du temps.",
        "Le cours a été retiré de l'emploi du temps.",
    )

    return redirect(
        f"{reverse('repartition_horaire')}"
        f"?annee_id={classe.annee_id}&classe_id={classe.id}"
    )
   
@transaction.atomic
def creer_repartition_horaire(request):

    # =====================================================
    # TRAITEMENT DU FORMULAIRE
    # =====================================================

    if request.method == "POST":

        form = RepartitionHoraireForm(
            request.POST
        )

        if form.is_valid():

            # -------------------------------------------------
            # CRÉATION DE L'OBJET SANS ENREGISTREMENT
            # -------------------------------------------------

            repartition = form.save(
                commit=False
            )

            # -------------------------------------------------
            # RÉCUPÉRATION DE LA MATIÈRE AFFECTÉE
            # -------------------------------------------------

            affectation_matiere = (
                form.cleaned_data[
                    "affectation_matiere"
                ]
            )

            # -------------------------------------------------
            # RECHERCHE DE L'AFFECTATION ENSEIGNANT
            #
            # Une Affectation relie :
            #
            # Enseignant
            #      ↓
            # Affectation
            #      ↓
            # AffectationMatiere
            # -------------------------------------------------

            try:

                affectation = (
                    Affectation.objects

                    .select_related(
                        "enseignant",
                        "affectation_matiere",
                    )

                    .get(
                        affectation_matiere=
                        affectation_matiere,

                        actif=True,
                    )
                )

            except Affectation.DoesNotExist:

                form.add_error(
                    "affectation_matiere",
                    (
                        "Cette matière n'a pas encore "
                        "d'enseignant actif affecté "
                        "à cette classe."
                    )
                )

                message_vers_notification(request, 'ERROR', (
                        "Impossible d'enregistrer "
                        "la répartition horaire."
                    ), (
                        "Impossible d'enregistrer "
                        "la répartition horaire."
                    ))

            except Affectation.MultipleObjectsReturned:

                form.add_error(
                    "affectation_matiere",
                    (
                        "Plusieurs enseignants actifs "
                        "sont affectés à cette matière. "
                        "Veuillez vérifier les "
                        "affectations."
                    )
                )

                message_vers_notification(request, 'ERROR', (
                        "Impossible d'enregistrer "
                        "la répartition horaire."
                    ), (
                        "Impossible d'enregistrer "
                        "la répartition horaire."
                    ))

            else:

                # ---------------------------------------------
                # AFFECTATION AUTOMATIQUE
                #
                # Le modèle RepartitionHoraire possède
                # un champ "affectation".
                # ---------------------------------------------

                repartition.affectation = (
                    affectation
                )

                # ---------------------------------------------
                # VALIDATION COMPLÈTE
                #
                # Cette validation vérifie notamment :
                #
                # - conflit de classe
                # - conflit d'enseignant
                # - créneau de cours
                # - année scolaire
                # - volume horaire hebdomadaire
                # ---------------------------------------------

                repartition.full_clean()

                # ---------------------------------------------
                # ENREGISTREMENT
                # ---------------------------------------------

                repartition.save()

                # ---------------------------------------------
                # MESSAGE
                # ---------------------------------------------

                message_vers_notification(request, 'SUCCESS', (
                        "La répartition horaire a été "
                        "enregistrée avec succès."
                    ), (
                        "La répartition horaire a été "
                        "enregistrée avec succès."
                    ))

                # ---------------------------------------------
                # REDIRECTION
                # ---------------------------------------------

                return redirect(
                    "liste_repartition_horaire"
                )

        else:

            message_vers_notification(request, 'ERROR', (
                    "Veuillez corriger les erreurs "
                    "du formulaire."
                ), (
                    "Veuillez corriger les erreurs "
                    "du formulaire."
                ))

    # =====================================================
    # AFFICHAGE INITIAL
    # =====================================================

    else:

        form = RepartitionHoraireForm()

    # =====================================================
    # AFFICHAGE
    # =====================================================

    return render(
        request,
        "horaire/creer_repartition_horaire.html",
        {
            "form": form,
        }
    )

def tableau_bord_repartition_horaire(request):

    # =====================================================
    # ANNÉE SCOLAIRE SÉLECTIONNÉE
    # =====================================================

    annee_id = request.GET.get(
        "annee"
    )

    annees = (
        AnneeScolaire.objects
        .all()
        .order_by(
            "-date_debut"
        )
    )

    annee_selectionnee = None

    if annee_id:

        annee_selectionnee = (
            AnneeScolaire.objects
            .filter(
                id=annee_id
            )
            .first()
        )

    # =====================================================
    # PAR DÉFAUT :
    # ANNÉE ACTIVE
    # =====================================================

    if not annee_selectionnee:

        annee_selectionnee = (
            AnneeScolaire.objects
            .filter(
                statut=AnneeScolaire.ACTIVE
            )
            .first()
        )

    # =====================================================
    # SI AUCUNE ANNÉE ACTIVE
    # =====================================================

    if not annee_selectionnee:

        annee_selectionnee = (
            AnneeScolaire.objects
            .order_by(
                "-date_debut"
            )
            .first()
        )

    # =====================================================
    # CLASSES DE L'ANNÉE
    # =====================================================

    classes = (
        Classe.objects
        .filter(
            annee=annee_selectionnee,
            actif=True,
        )
        .select_related(
            "niveau",
            "section",
            "annee",
        )
        .order_by(
            "niveau__ordre",
            "code",
        )
    )

    # =====================================================
    # STATISTIQUES PAR CLASSE
    # =====================================================

    classes_horaires = []

    for classe in classes:

        # -------------------------------------------------
        # HEURES PRÉVUES
        #
        # Somme des heures définies dans
        # AffectationMatiere
        # -------------------------------------------------

        heures_prevues = (
            AffectationMatiere.objects
            .filter(
                classe=classe,
                actif=True,
            )
            .aggregate(
                total=Sum(
                    "heures_par_semaine"
                )
            )
            ["total"]
            or 0
        )

        # -------------------------------------------------
        # HEURES RÉPARTIES
        #
        # Nombre réel de cours placés dans
        # RepartitionHoraire
        # -------------------------------------------------

        heures_reparties = (
            RepartitionHoraire.objects
            .filter(
                affectation__affectation_matiere__classe=classe,
                affectation__actif=True,
                affectation__affectation_matiere__actif=True,
                actif=True,
            )
            .count()
        )

        # -------------------------------------------------
        # HEURES RESTANTES
        # -------------------------------------------------

        heures_restantes = max(
            heures_prevues - heures_reparties,
            0,
        )

        # -------------------------------------------------
        # POURCENTAGE D'AVANCEMENT
        # -------------------------------------------------

        if heures_prevues > 0:

            pourcentage = round(
                (
                    heures_reparties
                    / heures_prevues
                )
                * 100
            )

        else:

            pourcentage = 0

        # -------------------------------------------------
        # ÉTAT
        # -------------------------------------------------

        if heures_prevues == 0:

            etat = "NON_CONFIGUREE"

        elif heures_restantes == 0:

            etat = "COMPLETE"

        else:

            etat = "INCOMPLETE"

        # -------------------------------------------------
        # AJOUT DES DONNÉES
        # -------------------------------------------------

        classes_horaires.append(
            {
                "classe": classe,

                "heures_prevues": (
                    heures_prevues
                ),

                "heures_reparties": (
                    heures_reparties
                ),

                "heures_restantes": (
                    heures_restantes
                ),

                "pourcentage": (
                    min(
                        pourcentage,
                        100
                    )
                ),

                "etat": etat,
            }
        )

    # =====================================================
    # STATISTIQUES GLOBALES
    # =====================================================

    total_classes = len(
        classes_horaires
    )

    classes_completes = len(
        [
            item
            for item in classes_horaires
            if item["etat"] == "COMPLETE"
        ]
    )

    classes_incompletes = len(
        [
            item
            for item in classes_horaires
            if item["etat"] == "INCOMPLETE"
        ]
    )

    classes_non_configurees = len(
        [
            item
            for item in classes_horaires
            if item["etat"] == "NON_CONFIGUREE"
        ]
    )

    # =====================================================
    # CONTEXTE
    # =====================================================

    contexte = {

        "annees": annees,

        "annee_selectionnee": (
            annee_selectionnee
        ),

        "classes_horaires": (
            classes_horaires
        ),

        "total_classes": (
            total_classes
        ),

        "classes_completes": (
            classes_completes
        ),

        "classes_incompletes": (
            classes_incompletes
        ),

        "classes_non_configurees": (
            classes_non_configurees
        ),
    }

    # =====================================================
    # AFFICHAGE
    # =====================================================

    return render(
        request,
        "horaire/tableau_bord_repartition_horaire.html",
        contexte,
    )
    
def liste_repartition_horaire(request):

    # =====================================================
    # ANNÉE SÉLECTIONNÉE
    # =====================================================

    annee_id = request.GET.get(
        "annee"
    )


    # =====================================================
    # CLASSE SÉLECTIONNÉE
    # =====================================================

    classe_id = request.GET.get(
        "classe"
    )


    # =====================================================
    # ANNÉES SCOLAIRES
    # =====================================================

    annees = (
        AnneeScolaire.objects
        .all()
        .order_by(
            "-date_debut"
        )
    )


    # =====================================================
    # CLASSES
    # =====================================================

    classes = (
        Classe.objects
        .none()
    )


    # =====================================================
    # CLASSE SÉLECTIONNÉE
    # =====================================================

    classe_selectionnee = None


    # =====================================================
    # EMPLOI DU TEMPS
    # =====================================================

    emploi_du_temps = {}


    # =====================================================
    # CRÉNEAUX
    # =====================================================

    creneaux = []


    # =====================================================
    # JOURS
    # =====================================================

    jours = (
        RepartitionHoraire.JOUR_CHOICES
    )


    # =====================================================
    # SI UNE ANNÉE EST SÉLECTIONNÉE
    # =====================================================

    if annee_id:

        classes = (
            Classe.objects
            .filter(
                annee_id=annee_id,
                actif=True,
            )
            .select_related(
                "niveau",
                "section",
                "annee",
            )
            .order_by(
                "niveau__ordre",
                "code",
            )
        )


    # =====================================================
    # SI UNE CLASSE EST SÉLECTIONNÉE
    # =====================================================

    if (
        annee_id
        and classe_id
    ):

        # -------------------------------------------------
        # RÉCUPÉRATION DE LA CLASSE
        # -------------------------------------------------

        classe_selectionnee = (
            Classe.objects
            .filter(
                id=classe_id,
                annee_id=annee_id,
                actif=True,
            )
            .first()
        )


        # -------------------------------------------------
        # SI LA CLASSE EXISTE
        # -------------------------------------------------

        if classe_selectionnee:


            # =============================================
            # CRÉNEAUX DE COURS
            # =============================================

            creneaux = (
                CreneauHoraire.objects
                .filter(
                    configuration__annee_id=
                    annee_id,

                    type_creneau=
                    CreneauHoraire.TYPE_COURS,

                    actif=True,
                )
                .order_by(
                    "ordre"
                )
            )


            # =============================================
            # RÉPARTITIONS DE LA CLASSE
            # =============================================

            repartitions = (
                RepartitionHoraire.objects
                .filter(
                    actif=True,
                    affectation = affectation_matiere,
                    classe=classe_selectionnee,
                )
                .select_related(
                    "creneau",

                    "affectation",

                    "affectation__enseignant",

                    "affectation__affectation_matiere",

                    "affectation__"
                    "affectation_matiere__matiere",
                )
                .order_by(
                    "creneau__ordre"
                )
            )


            # =============================================
            # INITIALISATION DE LA GRILLE
            # =============================================

            for creneau in creneaux:

                ligne = {

                    "creneau":
                    creneau,

                    "cours":
                    {},

                }


                grille_emploi_du_temps.append(
                    ligne
                )

            # =============================================
            # PLACEMENT DES COURS
            # =============================================

            cours_par_position = {}
            for repartition in repartitions:

                cle = (

                        repartition.creneau_id,

                        repartition.jour,

                    )


                cours_par_position[
                    cle
                ] = repartition
            for ligne in grille_emploi_du_temps:

                creneau = (
                    ligne["creneau"]
                )


            for jour_code, jour_nom in jours:

                cle = (

                    creneau.id,

                    jour_code,

                )


                ligne["cours"][
                    jour_code
                ] = (
                    cours_par_position.get(
                        cle
                    )
                )
    # =====================================================
    # CONTEXTE
    # =====================================================

    context = {

        "annees":
        annees,

        "classes":
        classes,

        "annee_id":
        annee_id,

        "classe_id":
        classe_id,

        "classe_selectionnee":
        classe_selectionnee,

        "creneaux":
        creneaux,

        "jours":
        jours,

        "emploi_du_temps":
        emploi_du_temps,

    }


    # =====================================================
    # AFFICHAGE
    # =====================================================

    return render(
        request,

        "horaire/liste_repartition_horaire.html",

        context,
    )  

    
def accueil(request):
    return render(request, "accueil.html")
    
def dashboard_promoteur(request):
    from .models import Affectation, AffectationMatiere, Enseignant

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    classes = Classe.objects.filter(actif=True)
    if annee_active:
        classes = classes.filter(annee=annee_active)

    return render(request, "dashboard/promoteur.html", {
        "utilisateur": utilisateur,
        "annee_active": annee_active,
        "nombre_classes": classes.count(),
        "nombre_eleves": Eleve.objects.filter(actif=True).count(),
        "nombre_enseignants": Enseignant.objects.filter(actif=True).count(),
        "nombre_inscriptions": Inscription.objects.count(),
        "nombre_utilisateurs": Utilisateur.objects.filter(actif=True).count(),
        "nombre_affectations": Affectation.objects.count()
        + AffectationMatiere.objects.count(),
    })

def dashboard_prefet(request):
    return render(request, "dashboard/prefet.html")

def dashboard_directeur(request):
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return redirect("connexion")
    
    annee_active = AnneeScolaire.objects.filter(statut=AnneeScolaire.ACTIVE).first()
    
    nombre_utilisateurs = Utilisateur.objects.filter(actif=True).count()
    nombre_eleves = Eleve.objects.filter(actif=True).count()
    nombre_classes = Classe.objects.filter(actif=True).count()
    nombre_enseignants = Enseignant.objects.filter(actif=True).count()
    nombre_affectations = Affectation.objects.filter(actif=True).count()
    nombre_inscriptions = Inscription.objects.filter(statut=Inscription.ACTIVE).count()
    
    context = {
        "utilisateur": utilisateur,
        "annee_active": annee_active,
        "nombre_utilisateurs": nombre_utilisateurs,
        "nombre_eleves": nombre_eleves,
        "nombre_classes": nombre_classes,
        "nombre_enseignants": nombre_enseignants,
        "nombre_affectations": nombre_affectations,
        "nombre_inscriptions": nombre_inscriptions,
    }
    
    return render(request, "dashboard/directeur.html", context)


def _utilisateur_courant(request):
    """Retourne l'utilisateur connecte, ou None."""
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return None
    return Utilisateur.objects.filter(id=utilisateur_id, actif=True).first()


def _contexte_compteurs_ecole(request):
    """Compteurs d'ecole partages par les tableaux de bord.

    Les modeles « secretaire » et « admin » affichent les memes
    indicateurs (eleves, inscriptions, paiements valides, montant en
    caisse) mais leurs vues ne leur passaient aucun de ces Elements :
    les compteurs sortaient vides, et le modele admin masquait le
    defaut derriere un |default:"0". Regroupes ici, les deux
    tableaux de bord lisent la meme source.

    « Nouvelles inscriptions » compte les inscriptions des trente
    derniers jours : c'est une notion de recence, pas le cumul
    annuel, sans quoi le compteur vaudrait toujours le total.
    """
    from decimal import Decimal

    from .models import Paiement, Presence, SortieCaisse

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return None

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    aujourdhui = timezone.localdate()
    il_y_a_30_jours = aujourdhui - timedelta(days=30)

    classes = Classe.objects.filter(actif=True)
    if annee_active:
        classes = classes.filter(annee=annee_active)

    paiements_valides = Paiement.objects.filter(
        statut=Paiement.VALIDE
    )

    inscriptions_actives = Inscription.objects.filter(
        statut=Inscription.ACTIVE
    ).count()

    inscriptions_reinscription = Inscription.objects.filter(
        type_inscription=Inscription.REINSCRIPTION
    ).count()

    # Le solde de caisse oppose les entrees aux sorties validees : une
    # sortie non validee n'a pas encore decrete la caisse.
    entrees = (
        EntreeCaisse.objects
        .aggregate(total=Sum("montant"))["total"]
        or Decimal("0")
    )
    sorties = (
        SortieCaisse.objects
        .filter(statut=SortieCaisse.VALIDEE)
        .aggregate(total=Sum("montant"))["total"]
        or Decimal("0")
    )

    return {
        "utilisateur": utilisateur,
        "annee_active": annee_active,

        "nombre_eleves": Eleve.objects.filter(actif=True).count(),
        "nombre_inscriptions": inscriptions_actives,
        "nombre_classes": classes.count(),
        "nombre_enseignants": Enseignant.objects.filter(
            actif=True
        ).count(),
        "nombre_utilisateurs": Utilisateur.objects.filter(
            actif=True
        ).count(),

        "eleves_nouveaux": Inscription.objects.filter(
            date_inscription__gte=il_y_a_30_jours
        ).count(),

        "absences_aujourd": Presence.objects.filter(
            date_presence=aujourdhui,
            statut=Presence.ABSENT,
        ).count(),

        "paiements_valides": paiements_valides.count(),
        "montant_paiements_valides": (
            paiements_valides.aggregate(total=Sum("montant"))["total"]
            or Decimal("0")
        ),

        # Le tableau de bord admin distingue « inscriptions actives »
        # de « nouvelles » : les deux compteurs sont donc fournis
        # sous leurs deux noms plutot que de laisser un 0 defaut.
        "nombre_inscriptions_actives": inscriptions_actives,
        "paiements_en_attente": Paiement.objects.filter(
            statut=Paiement.ENREGISTRE
        ).count(),

        # Taux de reinscription : part des inscriptions declarees comme
        # reinscription. Une annee sans donnee affiche 0 plutot qu'une
        # division par zero.
        "taux_reinscription": (
            (
                Decimal(inscriptions_reinscription) * 100
                / Decimal(inscriptions_actives)
            ).quantize(Decimal("0.1"))
            if inscriptions_actives
            else Decimal("0.0")
        ),

        "montant_caisse": entrees - sorties,
        "caisse_ouverte": _caisse_ouverte(),
    }


def _contexte_tableau_de_bord_financier(request):
    """Contexte commun aux tableaux de bord comptabilite et caisse.

    Calcule les agregats de paiements / entrees / sorties de caisse ainsi
    que les series utilisees par les graphiques des templates.
    """
    from decimal import Decimal

    from django.db.models.functions import TruncDate, TruncMonth

    from .models import EntreeCaisse, Paiement, SortieCaisse

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return None

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    aujourdhui = timezone.localdate()
    debut_mois = aujourdhui.replace(day=1)
    debut_periode_jour = aujourdhui - timedelta(days=6)
    debut_periode_mois = (aujourdhui.replace(day=1) - timedelta(days=365))

    paiements_valides = Paiement.objects.filter(statut=Paiement.VALIDE)

    total_paiements = paiements_valides.aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0")

    paiements_mois = paiements_valides.filter(
        date_paiement__date__gte=debut_mois
    ).aggregate(total=Sum("montant"))["total"] or Decimal("0")

    total_entrees = EntreeCaisse.objects.aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0")

    total_sorties = SortieCaisse.objects.filter(
        statut=SortieCaisse.VALIDEE
    ).aggregate(total=Sum("montant"))["total"] or Decimal("0")

    # --- Serie des 7 derniers jours ---------------------------------
    par_jour_brut = (
        paiements_valides
        .filter(date_paiement__date__gte=debut_periode_jour)
        .annotate(jour=TruncDate("date_paiement"))
        .values("jour")
        .annotate(montant=Sum("montant"))
        .order_by("jour")
    )
    index_jour = {row["jour"]: row["montant"] or Decimal("0") for row in par_jour_brut}
    paiements_par_jour = [
        {
            "jour": (debut_periode_jour + timedelta(days=i)).strftime("%d/%m"),
            "montant": index_jour.get(debut_periode_jour + timedelta(days=i), Decimal("0")),
        }
        for i in range(7)
    ]

    # --- Serie des 12 derniers mois ---------------------------------
    par_mois_brut = (
        paiements_valides
        .filter(date_paiement__date__gte=debut_periode_mois)
        .annotate(mois=TruncMonth("date_paiement"))
        .values("mois")
        .annotate(montant=Sum("montant"))
        .order_by("mois")
    )
    index_mois = {row["mois"]: row["montant"] or Decimal("0") for row in par_mois_brut}

    MOIS_COURTS = ["janv.", "fevr.", "mars", "avr.", "mai", "juin",
                   "juil.", "aout", "sept.", "oct.", "nov.", "dec."]
    paiements_par_mois = []
    for i in range(11, -1, -1):
        total_mois = aujourdhui.year * 12 + aujourdhui.month - 1 - i
        annee_ref, mois_index = divmod(total_mois, 12)
        paiements_par_mois.append({
            "mois": f"{MOIS_COURTS[mois_index]} {str(annee_ref)[2:]}",
            "montant": index_mois.get(date(annee_ref, mois_index + 1, 1), Decimal("0")),
        })

    return {
        "utilisateur": utilisateur,
        "annee_active": annee_active,
        "total_paiements": total_paiements,
        "paiements_mois": paiements_mois,
        "total_entrees": total_entrees,
        "total_sorties": total_sorties,
        "paiements_par_jour": paiements_par_jour,
        "paiements_par_mois": paiements_par_mois,

        # Sans caisse ouverte, aucune entree ne peut etre portee : le
        # tableau de bord doit le dire plutot que d'afficher un solde
        # a zero sans explication.
        "caisse_ouverte": _caisse_ouverte(),
        "peut_ouvrir_caisse": utilisateur_a_permission(
            utilisateur, "caisse.ouvrir"
        ),
        "peut_fermer_caisse": utilisateur_a_permission(
            utilisateur, "caisse.fermer"
        ),
    }


def dashboard_comptabilite(request):
    contexte = _contexte_tableau_de_bord_financier(request)
    if contexte is None:
        return redirect("connexion")
    return render(request, "dashboard/comptabilite.html", contexte)

def dashboard_discipline(request):
    return render(request, "dashboard/discipline.html")

def dashboard_caisse(request):
    contexte = _contexte_tableau_de_bord_financier(request)
    if contexte is None:
        return redirect("connexion")
    return render(request, "dashboard/caisse.html", contexte)

def dashboard_secretaire(request):
    """Tableau de bord du secretariat.

    La vue rendait « dashboard/secretaire.html » sans aucun contexte,
    alors que le modele attend onze variables : compteurs d'eleves,
    d'inscriptions, de classes, d'enseignants, d'utilisateurs, nouvelles
    inscriptions, absences du jour, paiements valides et montant en
    caisse. Tout s'affichait a zero ou vide, y compris le montant des
    paiements valides.
    """
    contexte = _contexte_compteurs_ecole(request)
    if contexte is None:
        return redirect("connexion")

    return render(request, "dashboard/secretaire.html", contexte)

def dashboard_enseignant(request):
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return redirect("connexion")
    
    # Récupérer l'enseignant associé
    try:
        enseignant = Enseignant.objects.get(utilisateur=utilisateur, actif=True)
    except Enseignant.DoesNotExist:
        enseignant = None
    
    nombre_affectations = 0
    nombre_classes = 0
    nombre_evaluations = 0
    prochain_creneau = None
    
    if enseignant:
        nombre_affectations = Affectation.objects.filter(enseignant=enseignant, actif=True).count()
        classes_ids = Affectation.objects.filter(enseignant=enseignant, actif=True).values_list('affectation_matiere__classe', flat=True).distinct()
        nombre_classes = Classe.objects.filter(id__in=classes_ids, actif=True).count()
        # Pour les évaluations, on compte les évaluations des affectations de l'enseignant
        from .models import Evaluation
        nombre_evaluations = Evaluation.objects.filter(affectation__enseignant=enseignant).count()
        
        # Prochain créneau à venir
        from datetime import datetime
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        except:
            pass
        
        jours_semaine = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI']
        maintenant = datetime.now()
        jour_actuel = jours_semaine[maintenant.weekday()] if maintenant.weekday() < 6 else None
        heure_actuelle = maintenant.time()
        
        # Récupérer les créneaux de l'enseignant
        repartitions = RepartitionHoraire.objects.filter(
            affectation__enseignant=enseignant,
            actif=True
        ).select_related('creneau', 'affectation__affectation_matiere__classe', 'affectation__affectation_matiere__matiere')
        
        if jour_actuel:
            # Créneaux d'aujourd'hui qui n'ont pas encore commencé
            reps_aujourdhui = repartitions.filter(jour=jour_actuel, creneau__heure_debut__gt=heure_actuelle).order_by('creneau__heure_debut')
            if reps_aujourdhui.exists():
                prochain_creneau = reps_aujourdhui.first()
            else:
                # Chercher le prochain jour avec des cours
                for i in range(1, 7):
                    prochain_jour_idx = (maintenant.weekday() + i) % 6
                    prochain_jour = jours_semaine[prochain_jour_idx]
                    reps_prochain = repartitions.filter(jour=prochain_jour).order_by('creneau__heure_debut')
                    if reps_prochain.exists():
                        prochain_creneau = reps_prochain.first()
                        break
        else:
            # C'est dimanche, chercher à partir de lundi
            reps_lundi = repartitions.filter(jour='LUNDI').order_by('creneau__heure_debut')
            if reps_lundi.exists():
                prochain_creneau = reps_lundi.first()
    
    context = {
        "utilisateur": utilisateur,
        "enseignant": enseignant,
        "nombre_affectations": nombre_affectations,
        "nombre_classes": nombre_classes,
        "nombre_evaluations": nombre_evaluations,
        "prochain_creneau": prochain_creneau,
    }
    
    return render(request, "dashboard/enseignant.html", context)

def acces_refuse(request):
    return render(
        request,
        "acces_refuse.html"
    )
    
#consulter liste d'élèves
@permission_required("eleve.consulter")
def liste_eleves(request):

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    # Cartes de classes : le template affiche nombre_eleves par classe.
    classes = []
    for classe in (
        Classe.objects
        .filter(actif=True)
        .select_related("niveau", "section", "annee")
        .order_by("libelle")
    ):
        classes.append({
            "id": classe.id,
            "libelle": classe.libelle,
            "niveau": classe.niveau,
            "section": classe.section,
            "nombre_eleves": Inscription.objects.filter(
                classe=classe,
                statut=Inscription.ACTIVE,
            ).count(),
        })

    return render(
        request,
        "eleves/liste.html",
        {
            "utilisateur": _utilisateur_courant(request),
            "eleves": Eleve.objects.filter(actif=True).order_by("nom", "prenom"),
            "classes": classes,
            "annee_active": annee_active,
        }
    )


@permission_required("eleve.consulter")
def liste_tous_eleves(request):
    """Tous les élèves avec la classe qui leur est affectée.

    Une seule ligne par élève, rattachée à son inscription active. Un élève
    sans inscription active reste listé, avec la mention « Non affecté ».

    Filtres (GET) : recherche, classe, année, et uniquement les non affectés.
    """
    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    classes = list(
        Classe.objects
        .filter(actif=True)
        .select_related("niveau", "section", "annee")
        .order_by("libelle")
    )

    recherche = (request.GET.get("q") or "").strip()
    classe_id = request.GET.get("classe") or ""
    annee_id = request.GET.get("annee") or ""
    seulement_sans_classe = request.GET.get("sans_classe") == "1"

    # Inscription servant de reference : active, de l'annee la plus recente.
    inscription_ref = {}
    for inscription in (
        Inscription.objects
        .filter(statut=Inscription.ACTIVE)
        .select_related("classe", "classe__niveau", "classe__section", "annee")
    ):
        courante = inscription_ref.get(inscription.eleve_id)
        if courante is None:
            inscription_ref[inscription.eleve_id] = inscription
            continue
        # Conserve l'inscription de l'annee la plus recente.
        try:
            if (inscription.annee.date_debut or "") > (courante.annee.date_debut or ""):
                inscription_ref[inscription.eleve_id] = inscription
        except TypeError:
            pass

    lignes = []
    for eleve in Eleve.objects.filter(actif=True).order_by("nom", "prenom"):
        inscription = inscription_ref.get(eleve.id)
        classe = inscription.classe if inscription else None

        if classe_id and (not classe or str(classe.id) != classe_id):
            continue
        if annee_id and (
            not inscription or str(inscription.annee_id) != annee_id
        ):
            continue
        if seulement_sans_classe and classe is not None:
            continue

        if recherche:
            cible = " ".join(
                filter(
                    None,
                    [
                        eleve.matricule,
                        eleve.nom,
                        eleve.postnom,
                        eleve.prenom,
                        classe.libelle if classe else None,
                    ],
                )
            ).lower()
            if recherche.lower() not in cible:
                continue

        lignes.append({
            "eleve": eleve,
            "inscription": inscription,
            "classe": classe,
            "nom_complet": " ".join(
                filter(None, [eleve.nom, eleve.postnom, eleve.prenom])
            ),
        })

    return render(request, "eleves/liste_tous_eleves.html", {
        "utilisateur": _utilisateur_courant(request),
        "lignes": lignes,
        "classes": classes,
        "annees": AnneeScolaire.objects.all().order_by("-id"),
        "annee_active": annee_active,
        "q": recherche,
        "classe_id": classe_id,
        "annee_id": annee_id,
        "seulement_sans_classe": seulement_sans_classe,
        "total": len(lignes),
        "total_eleves": Eleve.objects.filter(actif=True).count(),
        "non_affectes": sum(
            1 for ligne in lignes if ligne["classe"] is None
        ),
    })


# ============================================================
# MON PROFIL
# ============================================================

def mon_profil(request):
    """
    Affiche le profil personnel de l'utilisateur connecté.
    """

    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return redirect("connexion")

    try:
        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        request.session.flush()
        message_vers_notification(
            request,
            "ERROR",
            "Compte introuvable.",
            "Compte utilisateur introuvable."
        )
        return redirect("connexion")

    try:
        compte = (
            CompteUtilisateur.objects
            .select_related("utilisateur")
            .get(utilisateur=utilisateur)
        )
    except CompteUtilisateur.DoesNotExist:
        message_vers_notification(
            request,
            "ERROR",
            "Compte introuvable.",
            "Aucun compte utilisateur associé."
        )
        return redirect("connexion")

    if request.method == "POST":

        action = request.POST.get("action", "password")

        if action == "photo":
            photo = request.FILES.get("photo_profil")
            if not photo:
                message_vers_notification(
                    request,
                    "ERROR",
                    "Aucun fichier.",
                    "Veuillez sélectionner une photo."
                )
                return redirect("mon_profil")

            if photo.size > 5 * 1024 * 1024:
                message_vers_notification(
                    request,
                    "ERROR",
                    "Fichier trop volumineux.",
                    "La photo ne doit pas dépasser 5 Mo."
                )
                return redirect("mon_profil")

            allowed_types = ["image/jpeg", "image/png", "image/webp"]
            if photo.content_type not in allowed_types:
                message_vers_notification(
                    request,
                    "ERROR",
                    "Format non supporté.",
                    "Formats acceptés : JPG, PNG, WebP."
                )
                return redirect("mon_profil")

            utilisateur.photo_profil = photo
            utilisateur.save(update_fields=["photo_profil"])

            message_vers_notification(
                request,
                "SUCCESS",
                "Photo modifiée.",
                "Votre photo de profil a été mise à jour."
            )
            return redirect("mon_profil")

        ancien_mot_de_passe = request.POST.get(
            "ancien_mot_de_passe",
            ""
        )

        nouveau_mot_de_passe = request.POST.get(
            "nouveau_mot_de_passe",
            ""
        )

        confirmation = request.POST.get(
            "confirmation",
            ""
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not ancien_mot_de_passe:

            message_vers_notification(
                request,
                "ERROR",
                "Champ requis.",
                "Veuillez saisir votre ancien mot de passe."
            )

            return redirect("mon_profil")

        if not nouveau_mot_de_passe:

            message_vers_notification(
                request,
                "ERROR",
                "Champ requis.",
                "Veuillez saisir le nouveau mot de passe."
            )

            return redirect("mon_profil")

        if nouveau_mot_de_passe != confirmation:

            message_vers_notification(
                request,
                "ERROR",
                "Mots de passe différents.",
                "Les deux nouveaux mots de passe ne correspondent pas."
            )

            return redirect("mon_profil")

        if len(nouveau_mot_de_passe) < 8:

            message_vers_notification(
                request,
                "ERROR",
                "Mot de passe trop court.",
                "Le nouveau mot de passe doit contenir au moins 8 caractères."
            )

            return redirect("mon_profil")

        if not check_password(ancien_mot_de_passe, compte.mot_de_passe_hash):

            message_vers_notification(
                request,
                "ERROR",
                "Ancien mot de passe incorrect.",
                "L'ancien mot de passe est incorrect."
            )

            return redirect("mon_profil")

        # ----------------------------------------------------
        # MODIFICATION
        # ----------------------------------------------------

        compte.mot_de_passe_hash = make_password(
            nouveau_mot_de_passe
        )

        compte.save(
            update_fields=["mot_de_passe_hash"]
        )

        message_vers_notification(
            request,
            "SUCCESS",
            "Mot de passe modifié.",
            "Votre mot de passe a été modifié avec succès."
        )

        return redirect("mon_profil")

    try:
        return render(
            request,
            "profil/mon_profil.html",
            {
                "utilisateur": utilisateur,
                "compte": compte,
            }
        )
    except Exception:
        message_vers_notification(
            request,
            "ERROR",
            "Erreur.",
            "Une erreur est survenue lors de l'affichage de la page."
        )
        return redirect("dashboard_admin")


# ============================================================
# NOTIFICATIONS
# ============================================================

def liste_notifications(request):
    """
    Affiche les notifications actives (non lues) de l'utilisateur.

    Une notification cliquée est marquée comme lue : elle quitte
    cette liste et devient consultable dans l'historique.
    """

    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return redirect("connexion")

    try:
        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        return redirect("connexion")

    if not utilisateur_a_permission(
        utilisateur,
        "notification.consulter",
    ):
        message_vers_notification(
            request,
            "ERROR",
            "Accès refusé.",
            "Vous n'avez pas l'autorisation de consulter les notifications."
        )
        return redirect("dashboard_admin")

    notifications = (
        notifications_pour_utilisateur(utilisateur)
        .filter(
            lu=False,
        )
    )

    try:
        return render(
            request,
            "notifications/liste.html",
            {
                "notifications": notifications,
                "nb_non_lues": nb_notifications_non_lues(utilisateur),
                "nb_lues": notifications_pour_utilisateur(
                    utilisateur
                ).filter(lu=True).count(),
            }
        )
    except Exception:
        message_vers_notification(
            request,
            "ERROR",
            "Erreur.",
            "Une erreur est survenue lors de l'affichage des notifications."
        )
        return redirect("dashboard_admin")


def historique_notifications(request):
    """
    Historique des notifications reçues : toutes les notifications
    déjà lues par l'utilisateur, de la plus récente à la plus ancienne.
    """

    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return redirect("connexion")

    try:
        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        return redirect("connexion")

    if not utilisateur_a_permission(
        utilisateur,
        "notification.consulter",
    ):
        message_vers_notification(
            request,
            "ERROR",
            "Accès refusé.",
            "Vous n'avez pas l'autorisation de consulter l'historique des notifications."
        )
        return redirect("liste_notifications")

    notifications = (
        notifications_pour_utilisateur(utilisateur)
        .filter(
            lu=True,
        )
    )

    try:
        return render(
            request,
            "notifications/historique.html",
            {
                "notifications": notifications,
                "nb_non_lues": nb_notifications_non_lues(utilisateur),
                "nb_lues": notifications.count(),
            }
        )
    except Exception:
        message_vers_notification(
            request,
            "ERROR",
            "Erreur.",
            "Une erreur est survenue lors de l'affichage de l'historique des notifications."
        )
        return redirect("liste_notifications")


def ouvrir_notification(request, destinataire_id):
    """
    Detail complet d'une notification + marquage comme lue.

    Appelee en AJAX au clic sur une notification : la notification
    disparait de la liste active et bascule dans l'historique.
    """

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Methode non autorisee.",
            },
            status=405,
        )

    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return JsonResponse(
            {
                "success": False,
                "message": "Session expiree.",
            },
            status=401,
        )

    try:
        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Session expiree.",
            },
            status=401,
        )

    if not utilisateur_a_permission(
        utilisateur,
        "notification.consulter",
    ):
        return JsonResponse(
            {
                "success": False,
                "message": "Acces refuse.",
            },
            status=403,
        )

    try:
        destinataire = (
            DestinataireNotification.objects
            .select_related(
                "notification",
                "notification__type_notification",
                "notification__utilisateur_createur",
            )
            .get(
                id=destinataire_id,
                utilisateur=utilisateur,
            )
        )
    except DestinataireNotification.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Notification introuvable.",
            },
            status=404,
        )

    try:
        marquer_comme_lue(destinataire.id)
    except ValidationError:
        return JsonResponse(
            {
                "success": False,
                "message": "Impossible de marquer la notification comme lue.",
            },
            status=404,
        )

    notification = destinataire.notification
    type_notification = notification.type_notification
    createur = notification.utilisateur_createur

    return JsonResponse(
        {
            "success": True,
            "notification": {
                "id": destinataire.id,
                "objet": notification.objet,
                "contenu": notification.contenu,
                "type_code": (
                    type_notification.code.lower()
                    if type_notification
                    else "info"
                ),
                "type_libelle": (
                    type_notification.libelle
                    if type_notification
                    else "Information"
                ),
                "date_creation": notification.date_creation.strftime(
                    "%d/%m/%Y à %H:%M"
                ),
                "createur": str(createur) if createur else "",
                "lu": True,
            },
            "nb_non_lues": nb_notifications_non_lues(utilisateur),
        }
    )


def marquer_notification_lue(request, destinataire_id):
    """
    Marque une notification comme lue.
    """

    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return JsonResponse(
            {"success": False},
            status=401,
        )

    try:
        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        return JsonResponse(
            {"success": False},
            status=401,
        )

    try:
        destinataire = (
            DestinataireNotification.objects
            .select_related("notification")
            .get(
                id=destinataire_id,
                utilisateur=utilisateur,
            )
        )
    except DestinataireNotification.DoesNotExist:
        return JsonResponse(
            {"success": False},
            status=404,
        )

    try:
        destinataire.lu = True
        destinataire.save(update_fields=["lu"])
        return JsonResponse({"success": True})
    except Exception:
        return JsonResponse({"success": False})


def ajax_notifications_recentes(request):
    """
    Retourne les notifications récentes pour le popup flottant.
    """

    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return JsonResponse(
            {"notifications": [], "nb_non_lues": 0},
            status=401,
        )

    try:
        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        return JsonResponse(
            {"notifications": [], "nb_non_lues": 0},
            status=401,
        )

    try:
        if not utilisateur_a_permission(
            utilisateur,
            "notification.consulter",
        ):
            return JsonResponse(
                {"notifications": [], "nb_non_lues": 0},
                status=403,
            )

        destinataires = notifications_pour_utilisateur(utilisateur)[:5]

        nb_non_lues = nb_notifications_non_lues(utilisateur)

        donnees = []

        for dest in destinataires:
            notif = dest.notification
            donnees.append({
                "id": dest.id,
                "objet": notif.objet,
                "contenu": notif.contenu,
                "date_creation": notif.date_creation.strftime("%d/%m/%Y %H:%M"),
                "lu": dest.lu,
                "type_code": notif.type_notification.code.lower() if notif.type_notification else "info",
            })

        return JsonResponse({
            "notifications": donnees,
            "nb_non_lues": nb_non_lues,
        })
    except Exception:
        return JsonResponse({
            "notifications": [],
            "nb_non_lues": 0,
        })


# ============================================================
# FONCTIONS MANQUANTES (ajoutées pour compatibilité)
# ============================================================

def mes_affectations(request):
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
        enseignant = Enseignant.objects.get(utilisateur=utilisateur, actif=True)
    except (Utilisateur.DoesNotExist, Enseignant.DoesNotExist):
        return redirect("connexion")

    affectations_qs = (
        Affectation.objects
        .select_related(
            "affectation_matiere",
            "affectation_matiere__classe",
            "affectation_matiere__classe__niveau",
            "affectation_matiere__classe__section",
            "affectation_matiere__matiere",
        )
        .filter(enseignant=enseignant, actif=True)
        .order_by(
            "affectation_matiere__classe__niveau__ordre",
            "affectation_matiere__classe__code",
            "affectation_matiere__matiere__libelle",
        )
    )

    # Prepare JSON for grid view (list view)
    affectations_json = []
    for a in affectations_qs:
        affectations_json.append({
            "id": a.id,
            "classe_id": a.affectation_matiere.classe.id,
            "classe_libelle": a.affectation_matiere.classe.libelle,
            "classe_niveau": str(a.affectation_matiere.classe.niveau) if a.affectation_matiere.classe.niveau else "",
            "classe_section": str(a.affectation_matiere.classe.section) if a.affectation_matiere.classe.section else "",
            "matiere_libelle": a.affectation_matiere.matiere.libelle,
            "heures_par_semaine": a.affectation_matiere.heures_par_semaine,
            "annee": str(a.affectation_matiere.classe.annee),
        })

    # Prepare schedule data for "Affectation hebdomadaire" grid
    repartitions = (
        RepartitionHoraire.objects
        .select_related(
            "creneau",
            "affectation",
            "affectation__affectation_matiere",
            "affectation__affectation_matiere__matiere",
            "affectation__affectation_matiere__classe",
        )
        .filter(
            affectation__enseignant=enseignant,
            actif=True,
        )
        .order_by("jour", "creneau__ordre")
    )

    # Build schedule grid data
    jours_ordre = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI"]
    jours_labels = {"LUNDI": "Lundi", "MARDI": "Mardi", "MERCREDI": "Mercredi", "JEUDI": "Jeudi", "VENDREDI": "Vendredi", "SAMEDI": "Samedi"}
    
    schedule_by_classe = {}
    all_creneaux = set()
    
    for r in repartitions:
        classe = r.affectation.affectation_matiere.classe
        classe_id = classe.id
        
        if classe_id not in schedule_by_classe:
            schedule_by_classe[classe_id] = {
                "classe_libelle": classe.libelle,
                "classe_niveau": str(classe.niveau) if classe.niveau else "",
                "classe_section": str(classe.section) if classe.section else "",
                "jours": {j: [] for j in jours_ordre}
            }
        
        creneau_key = r.creneau.ordre
        all_creneaux.add(creneau_key)
        
        schedule_by_classe[classe_id]["jours"][r.jour].append({
            "ordre": r.creneau.ordre,
            "heure_debut": r.creneau.heure_debut.strftime("%H:%M"),
            "heure_fin": r.creneau.heure_fin.strftime("%H:%M"),
            "matiere": r.affectation.affectation_matiere.matiere.libelle,
        })

    # Sort creneaux
    sorted_creneaux = sorted(all_creneaux)

    import json
    affectations_json_str = json.dumps(affectations_json, ensure_ascii=False)
    
    # Prepare schedule JSON for the modal
    schedule_json = {
        "jours": [jours_labels[j] for j in jours_ordre],
        "jours_codes": jours_ordre,
        "creneaux": sorted_creneaux,
        "classes": {}
    }
    for classe_id, data in schedule_by_classe.items():
        schedule_json["classes"][str(classe_id)] = data

    schedule_json_str = json.dumps(schedule_json, ensure_ascii=False)

    return render(request, "enseignant/mes_affectations.html", {
        "utilisateur": utilisateur,
        "enseignant": enseignant,
        "affectations": affectations_qs,
        "affectations_json": affectations_json_str,
        "schedule_json": schedule_json_str,
    })


def mes_evaluations(request):
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return redirect("connexion")
    return render(request, "dashboard/enseignant.html", {"utilisateur": utilisateur})


def saisie_notes(request, evaluation_id):
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return redirect("connexion")
    return render(request, "dashboard/enseignant.html", {"utilisateur": utilisateur})


def mes_eleves(request):
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return redirect("connexion")
    return render(request, "dashboard/enseignant.html", {"utilisateur": utilisateur})


def detail_eleve(request, eleve_id):
    """Fiche d'un eleve : identite, responsables et inscriptions.

    La vue rendait la liste des eleves en ignorant l'eleve demande, si
    bien qu'un clic sur un eleve n'affichait aucune information le
    concernant. Elle rend desormais eleves/detail_eleve.html.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    eleve = get_object_or_404(Eleve, id=eleve_id)

    inscriptions = (
        Inscription.objects
        .filter(eleve=eleve)
        .select_related("classe", "annee")
        .order_by("-annee__date_debut", "classe__code")
    )

    responsabilites = (
        ResponsabiliteScolaire.objects
        .filter(eleve=eleve)
        .select_related("responsable")
        .order_by("-principal", "id")
    )

    inscription_courante = inscriptions.filter(
        annee__statut=AnneeScolaire.ACTIVE
    ).first() or inscriptions.first()

    return render(
        request,
        "eleves/detail_eleve.html",
        {
            "utilisateur": utilisateur,
            "eleve": eleve,
            "inscriptions": inscriptions,
            "responsabilites": responsabilites,
            "inscription": inscription_courante,
        },
    )


def _formulaire_eleve(
    request,
    *,
    template,
    action_url,
    titre,
    soumission,
    eleve=None,
    initial=None,
    force_type=None,
):
    """Vue mutualisée par les 4 écrans élève.

    Utilise toujours InscriptionCompleteForm et un template unique, ce qui
    évite les formulaires vides ou divergents entre création, réinscription
    et modification.

    Args:
        eleve: élève à modifier (mode édition), None pour une création.
        initial: valeurs initiales supplémentaires (ex. année active).
        force_type: force le type d'inscription (réinscription).
    """
    from .forms import InscriptionCompleteForm

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    if request.method == "POST":
        form = InscriptionCompleteForm(
            request.POST, request.FILES, eleve=eleve
        )

        if form.is_valid():
            inscription = form.save()
            message_vers_notification(
                request, "SUCCESS",
                f"{inscription.eleve} : informations enregistrées.",
                f"{inscription.eleve} : informations enregistrées.",
            )
            return redirect("liste_inscriptions")

        message_vers_notification(
            request, "ERROR",
            "Le formulaire contient des erreurs. Vérifiez les champs signalés.",
            "Le formulaire contient des erreurs. Vérifiez les champs signalés.",
        )
    else:
        valeurs = dict(initial or {})
        if annee_active and "annee" not in valeurs:
            valeurs["annee"] = annee_active
        if force_type:
            valeurs["type_inscription"] = force_type

        form = InscriptionCompleteForm(initial=valeurs or None, eleve=eleve)

        # La réinscription affiche d'emblée le bulletin à vérifier.
        if force_type == Inscription.REINSCRIPTION:
            form.fields["bulletin_precedent_verifie"].initial = False

    return render(request, template, {
        "utilisateur": utilisateur,
        "form": form,
        "annee_active": annee_active,
        "titre": titre,
        "soumission": soumission,
        "action_url": action_url,
        "mode_edition": eleve is not None,
    })


def modifier_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    return _formulaire_eleve(
        request,
        template="eleves/formulaire_eleve.html",
        action_url=f"/eleves/{eleve.id}/modifier/",
        titre=f"Modifier {eleve}",
        soumission="Enregistrer les modifications",
        eleve=eleve,
    )


def _qr_code_etiquette(valeur, taille=220):
    """QR code au format data-uri, prêt pour une balise <img>.

    Renvoie None si la generation echoue : la carte reste imprimable,
    seule l'image est omise.
    """
    if not valeur:
        return None

    try:
        import qrcode
        import io
        import base64

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(str(valeur))
        qr.make(fit=True)

        image = qr.make_image(fill_color="black", back_color="white")

        tampon = io.BytesIO()
        image.save(tampon, format="PNG")

        return (
            "data:image/png;base64,"
            + base64.b64encode(tampon.getvalue()).decode("ascii")
        )
    except Exception:
        return None


def carte_eleve(request, eleve_id):
    """Carte de service eleve, prete a imprimer.

    La vue rendait la liste des eleves au lieu de la carte : le lien
    « Carte eleve » de la fiche ouvrait le tableau de bord.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    eleve = get_object_or_404(Eleve, id=eleve_id)

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    inscriptions = (
        Inscription.objects
        .filter(eleve=eleve)
        .select_related("classe", "annee")
        .order_by("-annee__date_debut", "classe__code")
    )

    inscription_active = (
        inscriptions.filter(annee=annee_active).first()
        if annee_active
        else None
    ) or inscriptions.first()

    return render(
        request,
        "eleves/carte_eleve.html",
        {
            "utilisateur": utilisateur,
            "eleve": eleve,
            "inscription_active": inscription_active,
            "qr_code": _qr_code_etiquette(
                eleve.matricule or f"ELEVE-{eleve.id}"
            ),
        },
    )


def carte_service_enseignant(request, enseignant_id):
    """Carte de service enseignant, prete a imprimer.

    La vue rendait le tableau de bord de l'enseignant au lieu de la
    carte : le bouton d'impression affichait la page d'accueil.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    enseignant = get_object_or_404(
        Enseignant.objects.select_related("utilisateur"),
        id=enseignant_id,
    )

    personne = enseignant.utilisateur

    return render(
        request,
        "enseignant/carte_service_enseignant.html",
        {
            "utilisateur": utilisateur,
            "enseignant": enseignant,
            "nom_complet": (
                f"{personne.nom} {personne.postnom or ''} {personne.prenom}"
            ).strip(),
            "qr_code": _qr_code_etiquette(
                enseignant.matricule or f"ENS-{enseignant.id}"
            ),
        },
    )


def _contexte_bulletin(bulletin):
    """Contexte commun aux templates de bulletin.

    Les templates attendent : bulletin, lignes, eleve, classe, annee,
    modele et resultat_annuel.
    """
    from .models import ModeleBulletin, ResultatAnnuel

    inscription = bulletin.inscription
    eleve = inscription.eleve
    classe = inscription.classe

    modele = None
    if classe and classe.niveau:
        modele = (
            ModeleBulletin.objects
            .filter(actif=True, niveau=classe.niveau)
            .order_by("-version")
            .first()
        )
    if modele is None:
        modele = ModeleBulletin.objects.filter(actif=True).order_by("-version").first()

    resultat_annuel = ResultatAnnuel.objects.filter(
        inscription=inscription,
        annee=bulletin.annee_scolaire,
    ).first()

    return {
        "bulletin": bulletin,
        "lignes": bulletin.lignes.select_related("matiere").order_by("ordre"),
        "eleve": eleve,
        "classe": classe,
        "annee": bulletin.annee_scolaire,
        "modele": modele,
        "resultat_annuel": resultat_annuel,
    }


def bulletin_eleve(request, eleve_id):
    from .models import Bulletin

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    eleve = get_object_or_404(Eleve.objects.all(), id=eleve_id)

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    bulletin = None
    if annee_active:
        bulletin = (
            Bulletin.objects
            .filter(inscription__eleve=eleve, annee_scolaire=annee_active)
            .first()
        )

    if bulletin is None:
        message_vers_notification(
            request, "WARNING",
            "Aucun bulletin n'est disponible pour cet eleve.",
            "Aucun bulletin n'est disponible pour cet eleve.",
        )
        return redirect("liste_eleves")

    contexte = _contexte_bulletin(bulletin)
    contexte["utilisateur"] = utilisateur
    return render(request, "eleves/bulletin_eleve.html", contexte)


def _contexte_eleves_classe(classe):
    """Donnees communes aux vues d'une liste d'eleves de classe.

    La liste des eleves est servie sous trois formes : page complete,
    fragment de popup et page A4 imprimee. Les trois ont besoin du
    meme contexte ; lecalcul en est factorise ici pour eviter que les
    versions divergent, comme c'etait le cas avec la popup qui heritait
    du gabarit general.
    """
    inscriptions = list(
        Inscription.objects
        .filter(classe=classe, statut=Inscription.ACTIVE)
        .select_related("eleve", "annee", "classe")
        .prefetch_related(
            "eleve__responsabilites__responsable"
        )
        .order_by("eleve__nom", "eleve__prenom")
    )

    # Le responsable principal est porte par l'eleve, pas par
    # l'inscription : une requete qui Cherche inscription.responsable
    # echoue, et le template affiche silencieusement une cellule vide.
    for inscription in inscriptions:
        principal = next(
            (
                responsabilite
                for responsabilite in inscription.eleve.responsabilites.all()
                if responsabilite.principal
            ),
            None,
        )

        if principal is None:
            principal = inscription.eleve.responsabilites.all().first()

        inscription.responsable_principal = principal

    nb_filles = sum(
        1
        for inscription in inscriptions
        if inscription.eleve.sexe == "F"
    )

    return {
        "classe": classe,
        "inscriptions": inscriptions,
        "annee": classe.annee,
        "nb_eleves": len(inscriptions),
        "nb_filles": nb_filles,
        "nb_garcons": len(inscriptions) - nb_filles,
        "maintenant": timezone.now(),
    }


def eleves_par_classe(request, classe_id):
    """Liste des eleves inscrits dans une classe.

    Trois rendus selon le parametre `format` :

    - absent        -> page complete (eleves/eleves_par_classe.html)
    - format=modal  -> fragment seul, a injecter dans la popup
                       (eleves/eleves_par_classe_modal.html)
    - format=impression -> page A4 (eleves/impression_liste_classe.html)

    Le fragment de popup ne doit surtout pas heriter du gabarit general :
    injecter un document complet dans la boite de dialogue cassait la
    mise en page.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    classe = get_object_or_404(
        Classe.objects.select_related("annee", "niveau", "section"),
        id=classe_id,
    )

    contexte = _contexte_eleves_classe(classe)
    contexte["utilisateur"] = utilisateur

    format_rendu = request.GET.get("format")

    if format_rendu == "modal":
        return render(
            request,
            "eleves/eleves_par_classe_modal.html",
            contexte,
        )

    if format_rendu == "impression":
        return render(
            request,
            "eleves/impression_liste_classe.html",
            contexte,
        )

    return render(
        request,
        "eleves/eleves_par_classe.html",
        contexte,
    )


def eleves_par_classe_pdf(request, classe_id):
    """Liste des eleves d'une classe mise en page pour l'impression.

    L'export PDF n'etait pas implemente : l'ancien lien redirigeait vers
    la page HTML, sans mise en page A4. On renvoie desormais la page
    d'impression, que l'utilisateur imprime depuis son navigateur.
    """
    return impression_liste_eleves(request, classe_id)


def impression_liste_eleves(request, classe_id):
    """Liste des eleves d'une classe, mise en page A4 paysage."""
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    classe = get_object_or_404(
        Classe.objects.select_related("annee", "niveau", "section"),
        id=classe_id,
    )

    contexte = _contexte_eleves_classe(classe)
    contexte["utilisateur"] = utilisateur

    return render(
        request,
        "eleves/impression_liste_classe.html",
        contexte,
    )


def creer_eleve(request):
    return _formulaire_eleve(
        request,
        template="eleves/formulaire_eleve.html",
        action_url="/eleves/creer/",
        titre="Nouvel élève",
        soumission="Enregistrer l'élève",
    )


def reinscription(request):
    return _formulaire_eleve(
        request,
        template="eleves/formulaire_eleve.html",
        action_url="/eleves/reinscription/",
        titre="Réinscription d'un élève",
        soumission="Enregistrer la réinscription",
        force_type=Inscription.REINSCRIPTION,
    )


def emploi_du_temps(request):
    """
    Affiche l'emploi du temps de l'enseignant connecté.

    Seuls les créneaux qui lui sont affectés sont affichés,
    pour l'année scolaire active.
    """

    utilisateur_id = request.session.get("utilisateur_id")

    if not utilisateur_id:
        return redirect("connexion")

    try:
        utilisateur = Utilisateur.objects.get(
            id=utilisateur_id,
            actif=True,
        )
    except Utilisateur.DoesNotExist:
        return redirect("connexion")

    # =========================================================
    # ENSEIGNANT CONNECTÉ
    # =========================================================

    enseignant = Enseignant.objects.filter(
        utilisateur=utilisateur,
        actif=True,
    ).first()

    # =========================================================
    # ANNÉE SCOLAIRE ACTIVE
    # =========================================================

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE,
    ).first()

    annee_id = request.GET.get("annee")

    if annee_id:

        annee_choisie = AnneeScolaire.objects.filter(
            id=annee_id,
        ).first()

        if annee_choisie:
            annee_active = annee_choisie

    # =========================================================
    # CRÉNEAUX DE L'ENSEIGNANT
    # =========================================================

    horaires = Horaire.objects.none()

    if annee_active and enseignant:

        horaires = (
            Horaire.objects
            .filter(
                annee=annee_active,
                actif=True,
                affectation__enseignant=enseignant,
                affectation__actif=True,
            )
            .select_related(
                "classe",
                "creneau",
                "affectation",
                "affectation__affectation_matiere",
                "affectation__affectation_matiere__matiere",
            )
            .order_by(
                "jour_semaine",
                "creneau__ordre",
            )
        )

    annees = AnneeScolaire.objects.order_by("-date_debut")

    return render(
        request,
        "enseignant/emploi_du_temps.html",
        {
            "utilisateur": utilisateur,
            "enseignant": enseignant,
            "annee_active": annee_active,
            "annees": annees,
            "horaires": horaires,
            "jours": Horaire.JOURS_SEMAINE,
        },
    )


def gestion_matieres_classes(request):
    utilisateur_id = request.session.get("utilisateur_id")
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except (Utilisateur.DoesNotExist, Exception):
        return redirect("connexion")
    try:
        classes = (
            Classe.objects
            .select_related("annee", "niveau", "section")
            .order_by("niveau__ordre", "code")
        )

        classes_data = []
        for classe in classes:
            lignes = _lignes_cours_classe(classe)
            affectations = AffectationMatiere.objects.filter(
                classe=classe,
                actif=True,
            )

            classes_data.append({
                "classe": classe,
                # Le programme officiel compte aussi : sans cela la carte
                # n'annonce que les cours saisis a la main.
                "nombre_affectations": len(lignes),
                "nombre_officiels": sum(
                    1 for ligne in lignes if not ligne["hors_programme"]
                ),
                "nombre_hors_programme": sum(
                    1 for ligne in lignes if ligne["hors_programme"]
                ),
                "nombre_avec_enseignant": Affectation.objects.filter(
                    affectation_matiere__in=affectations,
                    actif=True,
                ).count(),
                "est_niveau_bulletin": getattr(classe.niveau, "est_niveau_bulletin", False) if classe.niveau else False,
            })

        return render(request, "matieres/gestion_matieres.html", {
            "utilisateur": utilisateur,
            "classes_data": classes_data,
        })
    except Exception:
        return redirect("connexion")


def ajax_horaire_classe(request, classe_id):
    """Retourne l'horaire d'une classe pour le popup."""
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return JsonResponse({"success": False}, status=401)
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return JsonResponse({"success": False}, status=401)

    try:
        classe = Classe.objects.get(id=classe_id)
    except Classe.DoesNotExist:
        return JsonResponse({"success": False, "error": "Classe introuvable"}, status=404)

    try:
        repartitions = (
            RepartitionHoraire.objects
            .select_related(
                "creneau",
                "affectation",
                "affectation__affectation_matiere",
                "affectation__affectation_matiere__matiere",
            )
            .filter(
                affectation__affectation_matiere__classe=classe,
                actif=True,
            )
            .order_by("jour", "creneau__ordre")
        )

        jours = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI"]
        jour_labels = {"LUNDI": "Lundi", "MARDI": "Mardi", "MERCREDI": "Mercredi", "JEUDI": "Jeudi", "VENDREDI": "Vendredi", "SAMEDI": "Samedi"}

        emploi = {}
        for r in repartitions:
            jour = r.jour
            if jour not in emploi:
                emploi[jour] = []
            try:
                matiere_libelle = r.affectation.affectation_matiere.matiere.libelle
            except Exception:
                matiere_libelle = "Non définie"
            try:
                enseignant_libelle = str(
                    r.affectation.enseignant
                ).strip()
            except Exception:
                enseignant_libelle = ""
            heure_debut = "{}:{}".format(r.creneau.heure_debut.hour, str(r.creneau.heure_debut.minute).zfill(2))
            heure_fin = "{}:{}".format(r.creneau.heure_fin.hour, str(r.creneau.heure_fin.minute).zfill(2))
            emploi[jour].append({
                "ordre": r.creneau.ordre,
                "heure_debut": heure_debut,
                "heure_fin": heure_fin,
                "matiere": matiere_libelle,
                "enseignant": enseignant_libelle,
                "repartition_id": r.id,
            })

        # ---------------------------------------------------------
        # LIGNES DE LA GRILLE
        #
        # Les lignes viennent toujours de la configuration horaire.
        # Les deduire des seuls creneaux occupats ne montrait qu'une
        # partie de la semaine : des qu'un seul cours etait place, les
        # autres lignes disparaisaient au lieu de rester vides.
        # ---------------------------------------------------------

        all_creneaux = [
            {
                "ordre": creneau.ordre,
                "type": creneau.type_creneau,
                "heure_debut": "{}:{}".format(
                    creneau.heure_debut.hour,
                    str(creneau.heure_debut.minute).zfill(2),
                ),
                "heure_fin": "{}:{}".format(
                    creneau.heure_fin.hour,
                    str(creneau.heure_fin.minute).zfill(2),
                ),
            }
            for creneau in (
                CreneauHoraire.objects
                .filter(
                    configuration__annee=classe.annee,
                    actif=True,
                )
                .order_by("ordre")
            )
        ]

        ordres_configures = [
            creneau["ordre"] for creneau in all_creneaux
        ]

        # Un creneau place peut provenir d'une configuration
        # differente : on l'ajoute pour ne pas perdre le cours.
        for jour_code in jours:
            for cours in emploi.get(jour_code, []):
                if cours["ordre"] not in ordres_configures:
                    ordres_configures.append(cours["ordre"])
                    all_creneaux.append({
                        "ordre": cours["ordre"],
                        "type": CreneauHoraire.TYPE_COURS,
                        "heure_debut": cours["heure_debut"],
                        "heure_fin": cours["heure_fin"],
                    })

        all_creneaux.sort(key=lambda creneau: creneau["ordre"])

        result = {
            "jours": [jour_labels[j] for j in jours],
            "creneaux": all_creneaux,
            "emploi": {}
        }
        for jour_code in jours:
            jour_nom = jour_labels[jour_code]
            result["emploi"][jour_nom] = {}
            for cours in emploi.get(jour_code, []):
                result["emploi"][jour_nom][cours["ordre"]] = cours

        return JsonResponse({"success": True, "classe": classe.libelle, "emploi": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": "Erreur lors du chargement"}, status=500)


def impression_horaire_classe(request, classe_id):
    """Grille horaire d'une classe, mise en page pour l'impression.

    La grille reprend tous les creneaux configures, occupes ou non : une
    semaine a moitie programmee doit rester lisible et complete.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    classe = get_object_or_404(
        Classe.objects.select_related("annee", "niveau", "section"),
        id=classe_id,
    )

    jours_libelles = dict(
        RepartitionHoraire.JOUR_CHOICES
    )

    # Les pauses font partie de la journee : sans elles, la grille
    # presente 07:30-10:00 puis 10:20, ce qui masque le repos.
    creneaux = list(
        CreneauHoraire.objects
        .filter(
            configuration__annee=classe.annee,
            actif=True,
        )
        .order_by("ordre")
    )

    repartitions = (
        RepartitionHoraire.objects
        .filter(
            affectation__affectation_matiere__classe=classe,
            actif=True,
        )
        .select_related(
            "creneau",
            "affectation",
            "affectation__enseignant",
            "affectation__affectation_matiere",
            "affectation__affectation_matiere__matiere",
        )
        .order_by("jour", "creneau__ordre")
    )

    occupation = {}
    for repartition in repartitions:
        occupation[
            (repartition.jour, repartition.creneau_id)
        ] = repartition

    # La grille est preconstruite : un template ne peut pas appeler
    # une fonction a deux arguments, or la recherche d'un cours
    # demande le jour et le creneau.
    grille = []

    for creneau in creneaux:
        if creneau.type_creneau == CreneauHoraire.TYPE_PAUSE:
            # Une pause occupe toute la ligne : elle ne peut pas
            # recevoir de matiere.
            grille.append({
                "creneau": creneau,
                "est_pause": True,
                "cellules": [],
            })
            continue

        cellules = []

        for code, libelle in jours_libelles.items():
            cellules.append({
                "code": code,
                "libelle": libelle,
                "cours": occupation.get((code, creneau.id)),
            })

        grille.append({
            "creneau": creneau,
            "est_pause": False,
            "cellules": cellules,
        })

    nb_jours = len(jours_libelles)

    return render(
        request,
        "matieres/impression_horaire_classe.html",
        {
            "utilisateur": utilisateur,
            "classe": classe,
            "creneaux": creneaux,
            "grille": grille,
            "jours_libelles": jours_libelles,
            "nb_jours": nb_jours,
            "nb_creneaux": repartitions.count(),
            "volume_total": sum(
                Decimal(str(ligne.heures_par_semaine or 0))
                for ligne in AffectationMatiere.objects.filter(
                    classe=classe,
                    actif=True,
                )
            ),
            "imprime_le": timezone.now(),
        },
    )


def liste_matieres_classe(request, classe_id):
    """Liste des cours (matières) d'une classe.

    Source de vérité : les pondérations officielles issues de la commande
    `initialiser_bulletin` (table PonderationMatiere), restreintes au niveau
    de la classe et à sa section.

    AffectationMatiere n'ajoute aucune ligne : elle ne fait qu'annoter un
    cours déjà présent avec son volume horaire. Les cours sans affectation
    restent donc visibles, comme le veut le programme officiel.

    Supporte deux rendus :
    - page complète      -> matieres/liste_matieres_classe.html
    - overlay AJAX       -> matieres/liste_matieres_classe_modal.html (?format=modal)
    """
    from .models import PonderationMatiere

    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return redirect("connexion")

    classe = get_object_or_404(
        Classe.objects.select_related("annee", "niveau", "section"),
        id=classe_id,
    )

    # ---------------------------------------------------------
    # 1. Cours officiels : un par matiere
    # ---------------------------------------------------------
    # La base contient deux generations de ponderations pour les niveaux
    # specialises : des lignes sans section (identiques a la section ELEC)
    # et des lignes propres a chaque section. On regroupe par matiere et on
    # privilegie la ponderation de la section de la classe, sinon la ligne
    # sans section, afin de ne jamais afficher un cours en double.
    par_matiere = {}

    if classe.niveau:
        qs = (
            PonderationMatiere.objects
            .filter(niveau=classe.niveau, actif=True)
            .select_related("matiere", "matiere__domaine", "section")
            .order_by("matiere__libelle")
        )

        for ponderation in qs:
            # On ignore les ponderations d'une autre section.
            if (
                ponderation.section_id
                and ponderation.section_id != classe.section_id
            ):
                continue

            deja = par_matiere.get(ponderation.matiere_id)
            if deja is None:
                par_matiere[ponderation.matiere_id] = ponderation
                continue

            # La section de la classe l'emporte sur la ligne sans section.
            if ponderation.section_id and not deja.section_id:
                par_matiere[ponderation.matiere_id] = ponderation

    # ---------------------------------------------------------
    # 2. Annotations : affectations existantes pour cette classe
    # ---------------------------------------------------------
    affectations = {
        affectation.matiere_id: affectation
        for affectation in AffectationMatiere.objects
        .filter(classe=classe, actif=True)
        .select_related("matiere")
    }

    lignes = [
        {
            "matiere": ponderation.matiere,
            "ponderation": ponderation,
            "affectation": affectations.get(ponderation.matiere_id),
        }
        for ponderation in par_matiere.values()
    ]

    # ---------------------------------------------------------
    # 3. Cours saisis a la main sans equivalent officiel
    # ---------------------------------------------------------
    # La liste part du programme, mais un cours saisi manuellement ne
    # doit pas disparaitre de l'ecran : il reste affichable et
    # affectable, simplement signale comme hors programme.
    #
    # Le rapprochement reutilise _lignes_cours_classe afin que cette
    # page et la page de programmation affichent exactement la meme
    # liste. Une comparaison par ensemble de noms ecraserait un cours
    # saisi des lors qu'un cours officiel porte un nom neighbours :
    # "HISTOIRE" et "Algèbre" seraient alors purement et simplement
    # absents de l'ecran.
    detail_par_matiere = {}

    for ligne in _lignes_cours_classe(classe):
        detail_par_matiere[ligne["matiere"].id] = ligne

        if ligne["ponderation"] is None:
            lignes.append({
                "matiere": ligne["matiere"],
                "ponderation": None,
                "affectation": ligne["affectation_matiere"],
            })

    lignes.sort(
        key=lambda ligne: _cle_matiere(
            ligne["matiere"].libelle
        )
    )

    # ---------------------------------------------------------
    # 4. Enseignant, volume et creneaux occupes
    # ---------------------------------------------------------
    # La liste doit permettre de repondre a la question « ce cours est-il
    # vraiment programme ? » : il faut l'enseignant, le volume
    # hebdomadaire et les creneaux occupes, pas seulement un volume.
    libelles_jour = dict(
        RepartitionHoraire.JOUR_CHOICES
    )

    for ligne in lignes:
        detail = detail_par_matiere.get(
            ligne["matiere"].id
        )

        if detail is None:
            continue

        affectation = detail["affectation"]

        ligne["enseignant"] = (
            affectation.enseignant if affectation else None
        )
        ligne["volume"] = (
            detail["affectation_matiere"].heures_par_semaine
            if detail["affectation_matiere"]
            else 0
        )
        ligne["heures_restantes"] = detail["heures_restantes"]
        ligne["creneaux"] = [
            {
                "jour": repartition.jour,
                "jour_libelle": libelles_jour.get(
                    repartition.jour,
                    repartition.jour,
                ),
                "ordre": repartition.creneau.ordre,
                "heure_debut": "{:02d}:{:02d}".format(
                    repartition.creneau.heure_debut.hour,
                    repartition.creneau.heure_debut.minute,
                ),
                "heure_fin": "{:02d}:{:02d}".format(
                    repartition.creneau.heure_fin.hour,
                    repartition.creneau.heure_fin.minute,
                ),
            }
            for repartition in detail["repartitions"]
        ]
        ligne["jours_distincts"] = sorted(
            {
                repartition["jour_libelle"]
                for repartition in ligne["creneaux"]
            }
        )

    contexte = {
        "utilisateur": utilisateur,
        "classe": classe,
        "classe_id": classe_id,
        "matieres": lignes,
        # La liste estissue des ponderations officielles, completee
        # par les cours saisis manuellement hors programme.
        "source_matiere": "ponderation",
        "nb_cours": len(lignes),
        "nb_officiels": len(lignes) - sum(
            1 for ligne in lignes if ligne["ponderation"] is None
        ),
        "nb_hors_programme": sum(
            1 for ligne in lignes if ligne["ponderation"] is None
        ),
        "nb_affectes": sum(
            1 for ligne in lignes if ligne["affectation"] is not None
        ),
        "nb_programmes": sum(
            1 for ligne in lignes if ligne.get("creneaux")
        ),
        "total_volume": sum(
            ligne.get("volume") or 0 for ligne in lignes
        ),
    }

    format_rendu = request.GET.get("format")

    if format_rendu == "modal":
        return render(
            request,
            "matieres/liste_matieres_classe_modal.html",
            contexte,
        )

    if format_rendu == "impression":
        return render(
            request,
            "matieres/impression_liste_cours_classe.html",
            contexte,
        )

    return render(
        request,
        "matieres/liste_matieres_classe.html",
        contexte,
    )


def gestion_affectations_enseignants(request):
    return render(request, "dashboard/enseignant.html")


def ajax_matieres_disponibles_par_classe(request):
    """Matieres de la meme section/niveau non encore affectees a la classe.

    Le template creer_affectation_matiere.html appelle cette vue avec
    ?classe_id=<id> (parametre de requete, pas de chemin).
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"error": "Non authentifie"}, status=401)

    classe_id = request.GET.get("classe_id")
    if not classe_id:
        return JsonResponse({"error": "classe_id manquant"}, status=400)

    classe = Classe.objects.filter(id=classe_id, actif=True).first()
    if not classe:
        return JsonResponse({"error": "Classe introuvable"}, status=404)

    # Meme source que AffectationMatiereForm : seules les matieres issues de
    # la ponderation du niveau/section peuvent etre affectees a cette classe.
    from .forms import _matieres_ponderation_classe

    deja_affectees = AffectationMatiere.objects.filter(
        classe=classe
    ).values_list("matiere_id", flat=True)

    matieres = (
        _matieres_ponderation_classe(classe)
        .exclude(id__in=deja_affectees)
        .select_related("domaine")
        .order_by("libelle")
    )

    return JsonResponse({
        "matieres": [
            {
                "id": matiere.id,
                "nom": matiere.libelle,
                "code": matiere.code,
                "domaine": matiere.domaine.libelle if matiere.domaine else None,
            }
            for matiere in matieres
        ]
    })


def ajax_matieres_affectees_par_classe(request):
    """Matieres deja affectees a la classe, avec leur volume horaire."""
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"error": "Non authentifie"}, status=401)

    classe_id = request.GET.get("classe_id")
    if not classe_id:
        return JsonResponse({"error": "classe_id manquant"}, status=400)

    classe = Classe.objects.filter(id=classe_id, actif=True).first()
    if not classe:
        return JsonResponse({"error": "Classe introuvable"}, status=404)

    affectations = (
        AffectationMatiere.objects
        .filter(classe=classe)
        .select_related("matiere")
        .order_by("matiere__libelle")
    )

    return JsonResponse({
        "classe": classe.libelle,
        "matieres": [
            {
                "id": affectation.matiere_id,
                "nom": affectation.matiere.libelle,
                "code": affectation.matiere.code,
                "heures_par_semaine": affectation.heures_par_semaine,
                "actif": affectation.actif,
            }
            for affectation in affectations
        ]
    })


def ajax_matieres_programmation(request):
    """Cours d'une classe, avec leurs heures restantes.

    Le template se sert de `heures_restantes` pour n'afficher que les
    cours dont le volume hebdomadaire n'est pas encore atteint, et de
    `peut_programmer` pour interdire la selection d'un cours sans
    enseignant, une repartition horaire exigeant une affectation.

    La liste reunionne le programme officiel et les cours saisis a la
    main. Un cours officiel n'a ni volume ni enseignant tant qu'il n'a
    pas ete affecte : il est malgre tout renvoye, sinon il resterait
    invisible et impossible a rattrapper depuis cette page.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"error": "Non authentifie"}, status=401)

    classe_id = request.GET.get("classe_id")
    if not classe_id:
        return JsonResponse({"error": "classe_id manquant"}, status=400)

    classe = Classe.objects.filter(id=classe_id, actif=True).first()
    if not classe:
        return JsonResponse({"error": "Classe introuvable"}, status=404)

    matieres = []

    for ligne in _lignes_cours_classe(classe):
        matiere = ligne["matiere"]

        if not matiere.actif:
            continue

        affectation_matiere = ligne["affectation_matiere"]
        affectation = ligne["affectation"]
        ponderation = ligne["ponderation"]

        volume = (
            Decimal(str(affectation_matiere.heures_par_semaine))
            if affectation_matiere
            else Decimal("0")
        )
        programmees = sum(
            (
                Decimal(str(_duree_creneau_en_heures(r.creneau)))
                for r in ligne["repartitions"]
            ),
            Decimal("0"),
        )
        restantes = volume - programmees

        enseignant = ""
        if affectation and affectation.enseignant:
            enseignant = str(affectation.enseignant).strip()

        creneaux_places = [
            {
                "repartition_id": repartition.id,
                "jour": repartition.jour,
                "creneau_id": repartition.creneau_id,
                "ordre": repartition.creneau.ordre,
                "heure_debut": repartition.creneau.heure_debut.strftime("%H:%M"),
                "heure_fin": repartition.creneau.heure_fin.strftime("%H:%M"),
            }
            for repartition in ligne["repartitions"]
        ]

        matieres.append({
            "id": affectation_matiere.id if affectation_matiere else None,
            "affectation_id": affectation.id if affectation else None,
            "matiere_id": matiere.id,
            "nom": matiere.libelle,
            "code": matiere.code,
            "enseignant": enseignant,
            "heures_par_semaine": float(volume),
            "heures_programmees": float(programmees),
            "heures_restantes": float(restantes if restantes > 0 else 0),
            "peut_programmer": bool(affectation and restantes > 0),
            # Un cours reste selectionnable meme sans enseignant : c'est
            # justement depuis ce panneau qu'on lui en affecte un.
            "cliquable": True,
            "source": "ponderation" if ponderation else "affectation",
            "hors_programme": bool(ligne["hors_programme"]),
            "ponderation_id": ponderation.id if ponderation else None,
            "travaux_journaliers_max": (
                ponderation.travaux_journaliers_max if ponderation else None
            ),
            "examen_max": ponderation.examen_max if ponderation else None,
            "creneaux_places": creneaux_places,
        })

    configuration = ConfigurationHoraire.objects.filter(
        annee=classe.annee
    ).first()

    creneaux = (
        CreneauHoraire.objects
        .filter(
            configuration=configuration,
            type_creneau=CreneauHoraire.TYPE_COURS,
            actif=True,
        )
        .order_by("ordre")
        if configuration
        else CreneauHoraire.objects.none()
    )

    enseignants = (
        Enseignant.objects
        .filter(actif=True, utilisateur__actif=True)
        .select_related("utilisateur")
        .order_by("utilisateur__nom", "utilisateur__prenom")
    )

    return JsonResponse({
        "classe": classe.libelle,
        "classe_id": classe.id,
        "matieres": matieres,
        "nb_officiels": sum(
            1 for m in matieres if m["source"] == "ponderation"
        ),
        "nb_hors_programme": sum(
            1 for m in matieres if m["hors_programme"]
        ),
        "enseignants": [
            {
                "id": enseignant.id,
                "nom": str(enseignant).strip(),
            }
            for enseignant in enseignants
        ],
        "creneaux": [
            {
                "id": creneau.id,
                "ordre": creneau.ordre,
                "heure_debut": creneau.heure_debut.strftime("%H:%M"),
                "heure_fin": creneau.heure_fin.strftime("%H:%M"),
            }
            for creneau in creneaux
        ],
        "jours": [
            {"code": code, "libelle": libelle}
            for code, libelle in RepartitionHoraire.JOUR_CHOICES
        ],
    })


def ajax_modifier_cours(request):
    """Enregistre les modifications d'un cours depuis le popup de programmation.

    Le cours etant selectionnable des la liste, cette vue doit couvrir les
    trois reglages possibles : la ponderation officielle, le volume
    hebdomadaire et l'affectation de l'enseignant, puis la pose ou le
    retrait d'un creneau. Toutes les actions renvoient la meme forme de
    reponse pour que le panneau se recharge sans Refresh.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"error": "Non authentifie"}, status=401)

    if request.method != "POST":
        return JsonResponse({"error": "Methode non autorisee"}, status=405)

    classe = Classe.objects.filter(
        id=request.POST.get("classe_id"),
        actif=True,
    ).first()
    matiere = Matiere.objects.filter(
        id=request.POST.get("matiere_id"),
        actif=True,
    ).first()

    if not classe or not matiere:
        return JsonResponse(
            {"error": "Classe ou matière introuvable."},
            status=404,
        )

    action = request.POST.get("action")

    # ---------------------------------------------------------
    # PONDERATION ET VOLUME
    # ---------------------------------------------------------
    if action == "enregistrer":

        # =====================================================
        # PONDÉRATION : VALIDEES AVANT TOUT ACCÈS EN BASE
        #
        # Les valeurs sont lues et controlees meme si aucune ligne
        # de ponderation n'existe encore. Valider apres coup la
        # laissait passer une saisie negative en silence : la ligne
        # n'existant pas, la boucle n'avait rien a controler.
        # =====================================================

        saisies = {}

        for champ in ("travaux_journaliers_max", "examen_max"):

            valeur = request.POST.get(champ)

            if valeur is None or valeur == "":
                continue

            try:
                valeur = int(valeur)
            except (TypeError, ValueError):
                return JsonResponse(
                    {"error": f"Le champ « {champ} » doit être un nombre entier."},
                    status=400,
                )

            if valeur < 0:
                return JsonResponse(
                    {"error": "Les valeurs de pondération ne peuvent pas être négatives."},
                    status=400,
                )

            saisies[champ] = valeur

        ponderation = PonderationMatiere.objects.filter(
            niveau=classe.niveau,
            matiere=matiere,
            actif=True,
        ).first()

        if ponderation is None:
            ponderation = PonderationMatiere.objects.filter(
                niveau=classe.niveau,
                matiere=matiere,
                actif=True,
                section=classe.section,
            ).first()

        if ponderation is None and saisies:
            section = classe.section

            if request.POST.get("meme_section") != "1":
                section = None

            ponderation, cree = PonderationMatiere.objects.get_or_create(
                niveau=classe.niveau,
                section=section,
                matiere=matiere,
                defaults={
                    "travaux_journaliers_max": 0,
                    "examen_max": 0,
                    "actif": True,
                },
            )

        if ponderation is not None and saisies:
            modifie = False

            for champ, valeur in saisies.items():
                if getattr(ponderation, champ) != valeur:
                    setattr(ponderation, champ, valeur)
                    modifie = True

            if modifie:
                ponderation.save()

        volume = request.POST.get("heures_par_semaine")

        if volume not in (None, ""):
            try:
                volume = int(volume)
            except (TypeError, ValueError):
                return JsonResponse(
                    {"error": "Le volume horaire doit être un nombre entier."},
                    status=400,
                )

            if volume < 1:
                return JsonResponse(
                    {"error": "Le volume horaire doit être supérieur à zéro."},
                    status=400,
                )

            if volume > AffectationMatiere.HEURES_MAX_PAR_SEMAINE:
                return JsonResponse(
                    {
                        "error": (
                            f"{volume} h par semaine est impossible : "
                            f"le maximum est de "
                            f"{AffectationMatiere.HEURES_MAX_PAR_SEMAINE} h "
                            f"par cours et par semaine."
                        )
                    },
                    status=400,
                )

            affectation_matiere, _ = _affectation_matiere_de(
                classe,
                matiere,
                creer=True,
            )

            if affectation_matiere.heures_par_semaine != volume:
                affectation_matiere.heures_par_semaine = volume
                affectation_matiere.save(
                    update_fields=["heures_par_semaine"]
                )

        return JsonResponse({"succes": True, "message": "Cours enregistré."})

    # ---------------------------------------------------------
    # ENSEIGNANT
    # ---------------------------------------------------------
    if action == "affecter_enseignant":

        volume = request.POST.get("heures_par_semaine") or 1

        try:
            volume = int(volume)
        except (TypeError, ValueError):
            return JsonResponse(
                {"error": "Le volume horaire doit être un nombre entier."},
                status=400,
            )

        if volume < 1:
            return JsonResponse(
                {"error": "Le volume horaire doit être supérieur à zéro."},
                status=400,
            )

        if volume > AffectationMatiere.HEURES_MAX_PAR_SEMAINE:
            return JsonResponse(
                {
                    "error": (
                        f"{volume} h par semaine est impossible : "
                        f"le maximum est de "
                        f"{AffectationMatiere.HEURES_MAX_PAR_SEMAINE} h "
                        f"par cours et par semaine."
                    )
                },
                status=400,
            )

        affectation_matiere, cree = _affectation_matiere_de(
            classe,
            matiere,
            creer=True,
        )

        if not cree and affectation_matiere.heures_par_semaine != volume:
            affectation_matiere.heures_par_semaine = volume
            affectation_matiere.save(
                update_fields=["heures_par_semaine"]
            )

        if request.POST.get("enseignant_id"):
            enseignant = (
                Enseignant.objects
                .filter(
                    id=request.POST.get("enseignant_id"),
                    actif=True,
                    utilisateur__actif=True,
                )
                .select_related("utilisateur")
                .first()
            )

            if not enseignant:
                return JsonResponse(
                    {"error": "Enseignant introuvable ou inactif."},
                    status=404,
                )

            affectation_existante = Affectation.objects.filter(
                affectation_matiere=affectation_matiere,
                actif=True,
            ).first()

            if affectation_existante:
                affectation_existante.enseignant = enseignant
                affectation_existante.save(
                    update_fields=["enseignant"]
                )
            else:
                Affectation.objects.create(
                    enseignant=enseignant,
                    affectation_matiere=affectation_matiere,
                    actif=True,
                )

        elif request.POST.get("retirer_enseignant") == "1":
            Affectation.objects.filter(
                affectation_matiere=affectation_matiere,
                actif=True,
            ).update(actif=False)

        return JsonResponse({
            "succes": True,
            "message": "Affectation de l'enseignant enregistrée.",
        })

    # ---------------------------------------------------------
    # CRENEAUX
    # ---------------------------------------------------------
    if action == "placer_creneau":

        affectation = Affectation.objects.filter(
            affectation_matiere__classe=classe,
            affectation_matiere__matiere=matiere,
            actif=True,
        ).first()

        if not affectation:
            return JsonResponse(
                {
                    "error": (
                        "Affectez d'abord un enseignant : un créneau "
                        "horaire est toujours lié à un enseignant."
                    )
                },
                status=400,
            )

        repartition = RepartitionHoraire(
            affectation=affectation,
            jour=request.POST.get("jour", ""),
            creneau_id=request.POST.get("creneau_id"),
        )

        try:
            repartition.full_clean()
            repartition.save()
        except ValidationError as erreur:
            return JsonResponse(
                {
                    "error": " ".join(
                        " ".join(str(v) for v in valeur)
                        for valeur in erreur.message_dict.values()
                    )
                },
                status=400,
            )
        except (IntegrityError, ValueError, TypeError):
            return JsonResponse(
                {"error": "Ce cours est déjà placé dans ce créneau."},
                status=400,
            )

        return JsonResponse({"succes": True, "message": "Créneau placé."})

    if action == "retirer_creneau":

        supprime, _ = RepartitionHoraire.objects.filter(
            id=request.POST.get("repartition_id"),
            affectation__affectation_matiere__classe=classe,
            actif=True,
        ).delete()

        if not supprime:
            return JsonResponse(
                {"error": "Créneau introuvable."},
                status=404,
            )

        return JsonResponse({"succes": True, "message": "Créneau retiré."})

    return JsonResponse({"error": "Action inconnue."}, status=400)


def ajax_creneaux_programmation(request):
    """Creneaux de cours encore libres pour une classe et un jour.

    Un creneau deja occupe par un autre cours de la meme classe est
    signale mais reste renvoye : le template permet de le distinguer
    des creneaux deja selectionnes dans le formulaire en cours de
    remplissage.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"error": "Non authentifie"}, status=401)

    classe_id = request.GET.get("classe_id")
    annee_id = request.GET.get("annee_id")
    jour = request.GET.get("jour")

    if not classe_id or not annee_id or not jour:
        return JsonResponse(
            {"error": "classe_id, annee_id et jour sont obligatoires"},
            status=400,
        )

    classe = Classe.objects.filter(id=classe_id, actif=True).first()
    if not classe:
        return JsonResponse({"error": "Classe introuvable"}, status=404)

    if classe.annee_id != int(annee_id):
        return JsonResponse(
            {"error": "La classe n'appartient pas a cette annee scolaire"},
            status=400,
        )

    if jour not in dict(RepartitionHoraire.JOUR_CHOICES):
        return JsonResponse({"error": "Jour invalide"}, status=400)

    creneaux = (
        CreneauHoraire.objects
        .filter(
            configuration__annee_id=annee_id,
            type_creneau=CreneauHoraire.TYPE_COURS,
            actif=True,
        )
        .order_by("ordre")
    )

    occupes = set(
        RepartitionHoraire.objects
        .filter(
            affectation__affectation_matiere__classe=classe,
            jour=jour,
            actif=True,
        )
        .values_list("creneau_id", flat=True)
    )

    # Un creneau occupe par le cours que l'on edite n'est pas un
    # conflit : le distinguer evite de le faire disparaitre de la
    # liste alors qu'il appartient a ce meme cours.
    affectation_id = request.GET.get("affectation_id")

    propres = set()

    if affectation_id:
        propres = set(
            RepartitionHoraire.objects
            .filter(
                affectation_id=affectation_id,
                affectation__affectation_matiere__classe=classe,
                jour=jour,
                actif=True,
            )
            .values_list("creneau_id", flat=True)
        )

    return JsonResponse({
        "classe": classe.libelle,
        "jour": jour,
        "creneaux": [
            {
                "id": creneau.id,
                "ordre": creneau.ordre,
                "libelle": creneau.__str__(),
                # Occupé par un autre cours : le créneau ne peut plus
                # être proposé, quel que soit le formulaire en cours.
                "deja_utilise": creneau.id in occupes,
                "propre": creneau.id in propres,
            }
            for creneau in creneaux
        ],
    })


def calendrier_scolaire(request):
    return render(request, "organisation/calendrier_scolaire.html")


def session_scolaire(request):
    return render(request, "organisation/session_scolaire.html")


def parcours_scolaire(request):
    utilisateur_id = request.session.get("utilisateur_id")
    if not utilisateur_id:
        return redirect("connexion")
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
    except Utilisateur.DoesNotExist:
        return redirect("connexion")
    return render(request, "organisation/parcours_scolaire.html", {"utilisateur": utilisateur})


def liste_inscriptions(request):
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    inscriptions = (
        Inscription.objects
        .select_related("eleve", "classe", "annee", "billet")
        .order_by("-annee__libelle", "classe__code", "eleve__nom")
    )

    return render(request, "inscription/liste_inscriptions.html", {
        "utilisateur": utilisateur,
        "annee_active": annee_active,
        "inscriptions": inscriptions,
    })


def creer_inscription(request):
    """Inscription complete : eleve + responsable(s) + inscription.

    Delegue a _formulaire_eleve pour partager le formulaire et le
    template avec la creation d'eleve, la reinscription et la modification.
    """
    return _formulaire_eleve(
        request,
        template="eleves/formulaire_eleve.html",
        action_url="/inscriptions/creer/",
        titre="Nouvelle inscription",
        soumission="Enregistrer l'inscription",
    )


def accueil_eleves_inscriptions(request):
    return liste_inscriptions(request)


def billet_inscription(request, inscription_id):
    """Billet d'inscription d'un eleve, mis en page pour l'impression.

    Le billet est cree a la premiere consultation puis reutilise : un
    numero d'edition doit rester stable, sinon deux exemplaires
    circulent sous deux identifiants differents. Une inscription
    annulee ou terminee garde son billet, celui-ci portant alors son
    statut, pour que l'archive reste lisible.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    inscription = get_object_or_404(
        Inscription.objects.select_related(
            "eleve",
            "annee",
            "classe",
            "classe__niveau",
            "classe__section",
        ),
        id=inscription_id,
    )

    billet, cree = BilletInscription.generer(
        inscription,
        utilisateur=utilisateur,
    )

    # Le responsable signe le billet : c'est le principal qui est
    # attendu, les autres figurent en second. Le responsable est porte
    # par l'eleve, pas par l'inscription.
    responsabilites = list(
        ResponsabiliteScolaire.objects
        .filter(eleve=inscription.eleve)
        .select_related("responsable")
    )

    principal = next(
        (
            responsabilite
            for responsabilite in responsabilites
            if responsabilite.principal
        ),
        None,
    )

    if principal is None:
        principal = next(
            (
                responsabilite
                for responsabilite in responsabilites
                if responsabilite.type_responsabilite
                in (
                    ResponsabiliteScolaire.PERE,
                    ResponsabiliteScolaire.MERE,
                )
            ),
            responsabilites[0] if responsabilites else None,
        )

    secondaires = [
        responsabilite
        for responsabilite in responsabilites
        if responsabilite is not principal
    ]

    # Les frais de l'annee sont rappeles a titre indicatif : le billet
    # atteste l'inscription, il n'est pas un releve de paiement.
    frais = (
        inscription.annee.frais_scolaires
        .filter(actif=True)
        .order_by("montant_total", "libelle")
        .first()
    )

    return render(
        request,
        "inscription/billet_inscription.html",
        {
            "utilisateur": utilisateur,
            "inscription": inscription,
            "billet": billet,
            "cree": cree,
            "responsable_principal": principal,
            "responsables_secondaires": secondaires,
            "frais": frais,
            "maintenant": timezone.now(),
        },
    )


def accueil_finances(request):
    return render(request, "comptabilite/liste_paiements.html")


def _caisse_ouverte():
    """ Premiere caisse ouverte, ou None.

    Une seule caisse a la fois est ouvertable : deux caisses ouvertes
    rendraient le solde dependant de laquelle on regarde.
    """
    return (
        Caisse.objects
        .filter(statut=Caisse.OUVERTE)
        .order_by("-id")
        .first()
    )


def _ouvrir_caisse_si_necessaire():
    """Caisse ouverte, ou nouvelle caisse ouverte si aucune ne l'est.

    Une seule caisse a la fois est ouverte : deux caisses ouvertes
    rendraient le solde dependant de laquelle on regarde.
    """
    caisse = _caisse_ouverte()

    if caisse is not None:
        return caisse

    maintenant = timezone.localtime()

    return Caisse.objects.create(
        libelle=f"Caisse du {maintenant:%d/%m/%Y %H:%M}",
        heure_ouverture=maintenant.time().replace(microsecond=0),
        # Caisse.clean exige une fermeture posterieure a l'ouverture.
        heure_fermeture=time(23, 59),
        statut=Caisse.OUVERTE,
    )


def _porter_en_caisse(paiement, utilisateur):
    """Cree l'entree de caisse correspondant a un paiement valide.

    L'entree est toujours creee : si aucune caisse n'est ouverte, une
    caisse l'est automatiquement. Ne pas le faire laissait l'argent
    recu hors caisse sans rien pour le signaler au-dela d'un avertissement
    — un solde de caisse faux, et aucun moyen de le reparer puisque
    la validation ne se rejoue plus une fois le statut VALIDE.

    Refuser la validation faute de caisse ouverte etait l'autre option :
    elle obligerait a ouvrir une caisse avant d'enregistrer le moindre
    versement. Un montant recu ne peut pas dependre d'une manipulation
    prealable.

    L'entree n'est pas validee ici : c'est a l'appelant de faire
    echouer la validation si l'entree est refusee.
    """
    caisse = _ouvrir_caisse_si_necessaire()

    return EntreeCaisse.objects.create(
        caisse=caisse,
        paiement=paiement,
        montant=paiement.montant,
        enregistre_par=utilisateur,
    )


@permission_requise("paiement.valider")
def valider_paiement(request, paiement_id):
    """ Validation d'un paiement, avec sa portee en caisse.

    Seul un paiement enregistre peut etre valide : valider deux fois le
    meme paiement creerait deux entrees de caisse pour un seul versement.
    L'ecriture de caisse suit la validation dans la meme transaction, et
    non comme une seconde operation a reussir : un paiement valide sans
    son entree de caisse rendrait le tableau de bord incoherent.
    """
    from .models import Paiement

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    paiement = get_object_or_404(
        Paiement.objects.select_related(
            "inscription",
            "inscription__eleve",
            "tranche",
            "tranche__frais",
            "enregistre_par",
        ),
        id=paiement_id,
    )

    if request.method != "POST":
        return redirect("liste_paiements")

    if paiement.statut != Paiement.ENREGISTRE:
        message_vers_notification(
            request,
            "WARNING",
            "Ce paiement n'est pas en attente de validation.",
            "Ce paiement n'est pas en attente de validation.",
        )
        return redirect("liste_paiements")

    # =========================================================
    # VALIDATION ET ÉCRITURE DE CAISSE
    # =========================================================

    entree = None
    refus = None

    with transaction.atomic():
        paiement.statut = Paiement.VALIDE
        paiement.valide_par = utilisateur

        # Le statut, son enregistrement et l'ecriture de caisse sont une
        # seule operation : un paiement valide sans son entree, ou une
        # entree d'un paiement non valide, fausseraient tous deux le
        # solde. full_clean seul ne suffirait pas, il ne persiste rien.
        try:
            paiement.full_clean()

            paiement.save(
                update_fields=["statut", "valide_par"]
            )

            entree = _porter_en_caisse(paiement, utilisateur)

            if entree is not None:
                entree.full_clean()

        except ValidationError as erreur:
            transaction.set_rollback(True)
            refus = " ".join(erreur.messages)

    # Le bloc est sorti : une transaction annulee refuse toute requete.
    # Le paiement doit donc etre relu apres, jamais dedans.
    if refus is not None:
        message_vers_notification(
            request,
            "ERROR",
            refus,
            refus,
        )
        return redirect("liste_paiements")

    paiement.refresh_from_db()

    if entree is None:
        message_vers_notification(
            request,
            "WARNING",
            f"Paiement de {paiement.montant} validé pour "
            f"{paiement.inscription.eleve}, mais aucune caisse n'est "
            f"ouverte : l'entrée n'a pas été portée en caisse.",
            f"Paiement de {paiement.montant} validé pour "
            f"{paiement.inscription.eleve}, mais aucune caisse n'est "
            f"ouverte : l'entrée n'a pas été portée en caisse.",
        )
    else:
        message_vers_notification(
            request,
            "SUCCESS",
            f"Paiement de {paiement.montant} validé pour "
            f"{paiement.inscription.eleve} et porté sur "
            f"« {entree.caisse.libelle} ».",
            f"Paiement de {paiement.montant} validé pour "
            f"{paiement.inscription.eleve} et porté sur "
            f"« {entree.caisse.libelle} ».",
        )

    return redirect("liste_paiements")


@permission_requise("paiement.annuler")
def annuler_paiement(request, paiement_id):
    """ Annulation d'un paiement, avec retrait de l'entree de caisse.

    L'annulation est le seul chemin qui rende son statut ENREGISTRE a un
    paiement. Elle ne porte que sur un paiement isole : solder une
    tranche puis annuler ce paiement laisserait la tranche ouverte sans
    que l'eleve soiturosi prevenu.
    """
    from .models import Paiement

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    paiement = get_object_or_404(
        Paiement.objects.select_related(
            "inscription",
            "inscription__eleve",
            "tranche",
        ),
        id=paiement_id,
    )

    if request.method != "POST":
        return redirect("liste_paiements")

    if paiement.statut == Paiement.ANNULE:
        message_vers_notification(
            request,
            "WARNING",
            "Ce paiement est déjà annulé.",
            "Ce paiement est déjà annulé.",
        )
        return redirect("liste_paiements")

    message_vers_notification(
        request,
        "SUCCESS",
        f"Paiement de {paiement.montant} annulé pour "
        f"{paiement.inscription.eleve}.",
        f"Paiement de {paiement.montant} annulé pour "
        f"{paiement.inscription.eleve}.",
    )

    with transaction.atomic():
        # L'entree de caisse ne peut pas rester : elle ferait
        # apparaitre un versement annule dans le solde.
        EntreeCaisse.objects.filter(
            paiement=paiement,
        ).delete()

        paiement.statut = Paiement.ANNULE
        paiement.valide_par = None
        paiement.save(update_fields=["statut", "valide_par"])

    return redirect("liste_paiements")


# ============================================================
# CAISSE
#
# Les permissions caisse.ouvrir / caisse.fermer existent depuis le
# seed, mais aucune vue ne les utilisait : une caisse ne pouvait
# naitre que par insertion manuelle en base. Sans caisse ouverte,
# _porter_en_caisse renvoyait None et tout paiement valide restait
# hors caisse, silencieusement.
# ============================================================

@permission_requise("caisse.ouvrir")
def ouvrir_caisse(request):
    """Ouvre une caisse, ou en cree une si l'etablissement n'en a pas.

    Une seule caisse ouverte a la fois : deux caisses ouvertes
    rendraient le solde dependant de laquelle on regarde.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    if request.method != "POST":
        return redirect("dashboard_caisse")

    if _caisse_ouverte() is not None:
        message_vers_notification(
            request,
            "WARNING",
            "Une caisse est déjà ouverte.",
            "Une caisse est déjà ouverte.",
        )
        return redirect("dashboard_caisse")

    caisse = _ouvrir_caisse_si_necessaire()

    message_vers_notification(
        request,
        "SUCCESS",
        f"Caisse « {caisse.libelle} » ouverte.",
        f"Caisse « {caisse.libelle} » ouverte.",
    )

    return redirect("dashboard_caisse")


@permission_requise("caisse.fermer")
def fermer_caisse(request):
    """Ferme la caisse ouverte.

    Les paiements deja valides restent valides : la caisse ne porte
    que l'ecriture de tresorerie, elle n'est pas la source de verite
    du statut d'un versement.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    if request.method != "POST":
        return redirect("dashboard_caisse")

    caisse = _caisse_ouverte()

    if caisse is None:
        message_vers_notification(
            request,
            "WARNING",
            "Aucune caisse n'est ouverte.",
            "Aucune caisse n'est ouverte.",
        )
        return redirect("dashboard_caisse")

    caisse.statut = Caisse.FERMEE
    caisse.save(update_fields=["statut"])

    message_vers_notification(
        request,
        "SUCCESS",
        f"Caisse « {caisse.libelle} » fermée.",
        f"Caisse « {caisse.libelle} » fermée.",
    )

    return redirect("dashboard_caisse")


@permission_requise("caisse.enregistrer_entree")
def porter_en_caisse(request, paiement_id):
    """Port un paiement deja valide dans la caisse ouverte.

    Couvre le cas que valider_paiement ne peut pas repare tout seul :
    un paiement valide alors qu'aucune caisse n'etait ouverte. Son
    statut ne repasse jamais par ENREGISTRE, donc la validation ne
    peut plus etre rejouee — sans cette vue, l'argent restait hors
    caisse sans aucun moyen de le reintegrer.
    """
    from .models import Paiement

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    paiement = get_object_or_404(
        Paiement.objects.select_related(
            "inscription", "inscription__eleve",
        ),
        id=paiement_id,
    )

    if request.method != "POST":
        return redirect("detail_paiement", paiement_id=paiement.id)

    if paiement.statut != Paiement.VALIDE:
        message_vers_notification(
            request,
            "WARNING",
            "Seul un paiement validé peut être porté en caisse.",
            "Seul un paiement validé peut être porté en caisse.",
        )
        return redirect("detail_paiement", paiement_id=paiement.id)

    if EntreeCaisse.objects.filter(paiement=paiement).exists():
        message_vers_notification(
            request,
            "WARNING",
            "Ce paiement est déjà porté en caisse.",
            "Ce paiement est déjà porté en caisse.",
        )
        return redirect("detail_paiement", paiement_id=paiement.id)

    caisse = _caisse_ouverte()

    if caisse is None:
        # Meme comportement que la validation : un montant recu ne
        # doit pas rester hors caisse faute d'une manipulation
        # prealable. La caisse s'ouvre donc ici aussi.
        caisse = _ouvrir_caisse_si_necessaire()

    entree = _porter_en_caisse(paiement, utilisateur)

    message_vers_notification(
        request,
        "SUCCESS",
        f"Paiement de {paiement.montant} porté sur « {caisse.libelle} ».",
        f"Paiement de {paiement.montant} porté sur « {caisse.libelle} ».",
    )

    return redirect("detail_paiement", paiement_id=paiement.id)


@permission_requise("recu.consulter")
def imprimer_recu(request, paiement_id):
    """Imprime le recu d'un paiement, au format A4 divise en huit.

    Le numero de recu est cree a la volee s'il manque encore : les
    paiements valides avant l'existence de cet ecran n'ont pas de
    recu, et le refuser laisserait ces versements sans justificatif.
    Le numero est derive de l'identifiant du paiement, donc unique
    et stable entre deux impressions.
    """
    from .models import Paiement, Recu

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    paiement = get_object_or_404(
        Paiement.objects.select_related(
            "inscription",
            "inscription__eleve",
            "inscription__classe",
            "inscription__annee",
            "tranche",
            "tranche__frais",
            "enregistre_par",
            "valide_par",
        ),
        id=paiement_id,
    )

    if paiement.statut not in (Paiement.VALIDE, Paiement.ENREGISTRE):
        message_vers_notification(
            request,
            "WARNING",
            "Un paiement annulé ne donne pas lieu à un reçu.",
            "Un paiement annulé ne donne pas lieu à un reçu.",
        )
        return redirect("detail_paiement", paiement_id=paiement.id)

    recu, _ = Recu.objects.get_or_create(
        paiement=paiement,
        defaults={
            "numero_recu": (
                f"R{paiement.date_paiement:%Y}{paiement.id:06d}"
            ),
            "statut": Recu.VALIDE,
        },
    )

    return render(
        request,
        "comptabilite/recu_impression.html",
        {
            "utilisateur": utilisateur,
            "paiement": paiement,
            "recu": recu,
        },
    )


@permission_requise("paiement.consulter")
def liste_paiements(request):
    """ Paiements enregistres, avec les actions de l'etat suivant.

    La liste est le seul endroit ou un paiement peut etre valide : sans
    elle, l'etat ENREGISTRE definitif que rien ne pouvait faire
    passer a VALIDE.
    """
    from .models import Paiement

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    paiements = (
        Paiement.objects
        .select_related(
            "inscription",
            "inscription__eleve",
            "inscription__classe",
            "tranche",
            "tranche__frais",
            "enregistre_par",
            "valide_par",
        )
        .order_by("-date_paiement", "-id")
    )

    # Un filtre par etat : la file des paiements a valider est ce que le
    # comptable ouvre en premier, et elle est invisible sans filtre.
    filtre = request.GET.get("statut", "")

    if filtre in dict(Paiement.STATUT_CHOICES):
        paiements = paiements.filter(statut=filtre)

    if request.GET.get("classe"):
        paiements = paiements.filter(
            inscription__classe_id=request.GET["classe"]
        )

    return render(
        request,
        "comptabilite/liste_paiements.html",
        {
            "utilisateur": utilisateur,
            "annee_active": annee_active,
            "paiements": paiements,
            "filtre": filtre,
            "nb_enregistres": Paiement.objects.filter(
                statut=Paiement.ENREGISTRE
            ).count(),
            "nb_valides": Paiement.objects.filter(
                statut=Paiement.VALIDE
            ).count(),
            "total_valide": (
                Paiement.objects
                .filter(statut=Paiement.VALIDE)
                .aggregate(total=Sum("montant"))["total"]
                or Decimal("0")
            ),
            "peut_valider": utilisateur_a_permission(
                utilisateur, "paiement.valider"
            ),
            "peut_annuler": utilisateur_a_permission(
                utilisateur, "paiement.annuler"
            ),
        }
    )


@permission_requise("paiement.consulter")
def detail_paiement(request, paiement_id):
    """ Detail d'un paiement et de sa position sur sa tranche. """
    from .models import Paiement, Recu

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    paiement = get_object_or_404(
        Paiement.objects.select_related(
            "inscription",
            "inscription__eleve",
            "inscription__classe",
            "inscription__annee",
            "tranche",
            "tranche__frais",
            "enregistre_par",
            "valide_par",
        ),
        id=paiement_id,
    )

    return render(
        request,
        "comptabilite/detail_paiement.html",
        {
            "utilisateur": utilisateur,
            "paiement": paiement,
            "reste_tranche": _reste_tranche(paiement.tranche),
            "entree": EntreeCaisse.objects.filter(
                paiement=paiement
            ).select_related("caisse").first(),
            "recu": Recu.objects.filter(paiement=paiement).first(),
            # La caisse ouverte permet au detail d proposer le report
            # d'un paiement valide qui n'a pas d'entree : sans elle,
            # l'agent ne voit pas ou l'argent doit aller.
            "caisse": _caisse_ouverte(),
            "peut_valider": utilisateur_a_permission(
                utilisateur, "paiement.valider"
            ),
            "peut_annuler": utilisateur_a_permission(
                utilisateur, "paiement.annuler"
            ),
        }
    )


@permission_requise("recu.consulter")
def liste_recus(request):
    """Recus emis, du plus recent au plus ancien.

    La vue rendait le template sans aucun contexte : la liste restait
    vide quelle que soit la base, et le lien « Voir » menait au
    paiement pour aucun element.
    """
    from .models import Recu

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    return render(
        request,
        "comptabilite/liste_recus.html",
        {
            "utilisateur": utilisateur,
            "recus": (
                Recu.objects
                .select_related(
                    "paiement",
                    "paiement__inscription",
                    "paiement__inscription__eleve",
                )
                .order_by("-date_generation")
            ),
        },
    )


@permission_requise("caisse.consulter")
def detail_caisse(request, caisse_id):
    return render(request, "comptabilite/detail_caisse.html")


def liste_classes_paiements(request):
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    classes = Classe.objects.filter(actif=True)
    if annee_active:
        classes = classes.filter(annee=annee_active)

    return render(request, "comptabilite/classes_paiements.html", {
        "utilisateur": utilisateur,
        "annee_active": annee_active,
        "classes": classes.select_related("niveau", "section").order_by(
            "niveau__ordre", "code"
        ),
    })


def eleves_classe_paiements(request, classe_id):
    from decimal import Decimal

    from django.db.models.functions import Coalesce

    from .models import Paiement

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    classe = get_object_or_404(
        Classe.objects.select_related("annee", "niveau", "section"),
        id=classe_id,
    )

    filtre = request.GET.get("filtre", "tous")

    inscriptions = (
        Inscription.objects
        .filter(classe=classe, statut=Inscription.ACTIVE)
        .select_related("eleve")
        .annotate(
            total_paye=Coalesce(
                Sum(
                    "paiements__montant",
                    filter=Q(paiements__statut=Paiement.VALIDE),
                ),
                Decimal("0.00"),
            )
        )
        .order_by("eleve__nom", "eleve__prenom")
    )

    eleves_data = [
        {
            "eleve": inscription.eleve,
            "inscription": inscription,
            "total_paye": inscription.total_paye,
            "a_paye": inscription.total_paye > Decimal("0"),
        }
        for inscription in inscriptions
    ]

    if filtre == "payes":
        eleves_data = [item for item in eleves_data if item["a_paye"]]
    elif filtre == "dettes":
        eleves_data = [item for item in eleves_data if not item["a_paye"]]

    return render(request, "comptabilite/eleves_classe_paiements.html", {
        "utilisateur": utilisateur,
        "classe": classe,
        "filtre": filtre,
        "eleves_data": eleves_data,
    })


def _id_ou_none(valeur):
    """Identifiant entier, ou None si le champ est absent ou invalide.

    Django leve une ValueError sur filter(id="") comme sur
    filter(id="abc") : le champ du formulaire n'est pas un
    identifiant, et une saisie non numerique doit se traduire par
    None — que la requete ne trouve rien — et non par une erreur 500.
    """
    if valeur is None:
        return None

    texte = str(valeur).strip()

    if not texte:
        return None

    if not re.fullmatch(r"[0-9]+", texte):
        return None

    return texte


def _tranches_avec_reste(frais_ids):
    """Tranches d'une inscription, avec leur reste a payer.

    L'ordre retenu est celui des echeances, pas celui du numero : les
    frais d'une annee sont saisis tranche par tranche, et le numero
    suit la creation, pas l'echeance.
    """
    from decimal import Decimal

    from django.db.models.functions import Coalesce

    from .models import Paiement, Tranche

    if not frais_ids:
        return []

    return list(
        Tranche.objects
        .filter(frais_id__in=frais_ids)
        .annotate(
            paye=Coalesce(
                Sum(
                    "paiements__montant",
                    filter=Q(paiements__statut=Paiement.VALIDE),
                ),
                Decimal("0.00"),
            )
        )
        .order_by("date_echeance", "numero", "id")
    )


def _tranche_a_solder(frais_ids):
    """Premiere tranche non soldee, seule encaissable.

    Les tranches se payent dans l'ordre des echeances : solder la
    troisieme en laissant la premiere impayee autoriserait un eleve a
    ne jamais payer la premiere. La fonction renvoie la premiere tranche
    dont le reste est positif, ou None si tout est solde.
    """
    for tranche in _tranches_avec_reste(frais_ids):
        reste = tranche.montant - (tranche.paye or Decimal("0.00"))

        if reste > 0:
            return tranche, reste

    return None, Decimal("0.00")


def _tranche_bloquante(tranche, frais_ids):
    """Tranche anterieure encore due, si la choisie n'est pas la bonne.

    Une tranche anterieure existe des qu'une echeance precede celle
    choisie. C'est cette tranche-la qui doit etre soldee en premier.
    """
    if tranche is None:
        return None

    for autre in _tranches_avec_reste(frais_ids):
        if autre.id == tranche.id:
            return None

        if (
            autre.date_echeance < tranche.date_echeance
            or (
                autre.date_echeance == tranche.date_echeance
                and autre.id < tranche.id
            )
        ):
            reste = autre.montant - (autre.paye or Decimal("0.00"))

            if reste > 0:
                return autre

    return None


def _valider_montant_paiement(valeur_saisie):
    """Convertit un montant saisi en Decimal positif.

    Le controle passe par Decimal et non par un simple float : un
    montant de 0.10 ne doit pas devenir 0.099999... en base.

    Le motif est volontairement le meme que celui du formulaire, cote
    navigateur : "12." et "12," sont des saisies inachevees que Python
    accepte volontiers (il y lit 12), et un montant trop vagy doit etre
    refuse des le navigateur pour ne pas.train l'utilisateur dans un
    aller-retour au serveur. Une valeur nulle, negative ou non
    numerique arrivera toujours par une autre voie — requete directe,
    script, autre poste : ce controle reste le dernier rempart.
    """
    from decimal import Decimal

    if valeur_saisie is None:
        raise ValidationError("Le montant est obligatoire.")

    texte = str(valeur_saisie).strip()

    if not texte:
        raise ValidationError("Le montant est obligatoire.")

    # [0-9] explicite : \d accepte aussi les chiffres d'autres
    # alphabets, que Decimal peut refuser dans une base de donnees
    # qui n'en attend pas.
    if not re.fullmatch(r"[0-9]+([.,][0-9]{1,2})?", texte):
        raise ValidationError(
            "Le montant doit être un nombre positif, avec au plus "
            "deux décimales (exemple : 125.50)."
        )

    # Virgule decimale utilisee en francais.
    if "," in texte:
        texte = texte.replace(",", ".")

    montant = Decimal(texte)

    if montant <= 0:
        raise ValidationError(
            "Le montant doit être supérieur à zéro : un paiement "
            "à 0 ou négatif n'est pas un paiement."
        )

    return montant


@permission_requise("paiement.enregistrer")
def encaisser_paiement(request):
    """Encaissement d'un paiement.

    Deux usages partagent la meme vue : la page dediee
    (comptabilite/encaisser_paiement.html) et le fragment injecte dans
    la fenetre de paiement de la page « Paiements eleves ». Les deux
    renvoie un fragment HTML si le template le demande, ce qui permet a
    la fenetre de rester ouverte sur le resultat sans rechargement.
    """
    from .models import Paiement, Tranche

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    contexte = {
        "utilisateur": utilisateur,
        "erreur": None,
        "erreurs": {},
        # Valeurs renvoyees pour ne pas perdre la saisie en cas
        # d'erreur de validation.
        "saisie": {},
    }

    if request.method == "POST":

        inscription_id = _id_ou_none(request.POST.get("inscription_id"))
        tranche_id = _id_ou_none(request.POST.get("tranche_id"))
        montant_saisi = request.POST.get("montant")

        contexte["saisie"] = {
            "inscription_id": inscription_id or "",
            "tranche_id": tranche_id or "",
            "montant": montant_saisi or "",
        }

        # =====================================================
        # CONTRÔLE DES SAISIES
        # =====================================================

        inscription = Inscription.objects.filter(
            id=inscription_id,
            statut=Inscription.ACTIVE,
        ).select_related("eleve", "annee", "classe").first()

        if inscription is None:
            contexte["erreurs"]["inscription_id"] = (
                "Sélectionnez une inscription active."
            )
        else:
            # Le fragment doit reafficher l'identite de l'eleve apres
            # une erreur : sans cela le formulaire se recharge vide et
            # la saisie est perdue.
            contexte["inscription"] = inscription

        frais_ids = (
            _frais_scolaires_de(inscription)
            if inscription is not None
            else []
        )

        tranche = Tranche.objects.filter(
            id=tranche_id,
        ).first() if tranche_id else None

        if tranche is None:
            contexte["erreurs"]["tranche_id"] = (
                "Sélectionnez une tranche."
            )
        elif tranche.frais_id not in frais_ids:
            # Une tranche d'une autre annee scolaire ne peut pas
            # solder cette inscription, meme si elle existe.
            contexte["erreurs"]["tranche_id"] = (
                "Cette tranche ne correspond pas aux frais "
                "scolaires de l'année de l'inscription."
            )
        else:
            # Les tranches se payent dans l'ordre des echeances.
            # Sans ce controle, un formulaire trafique — ou une ancienne
            # page encore en cache — autoriserait a solder la troisieme
            # tranche en laissant la premiere impayee.
            bloquee = _tranche_bloquante(tranche, frais_ids)

            if bloquee is not None:
                contexte["erreurs"]["tranche_id"] = (
                    f"La tranche {bloquee.numero}, échue le "
                    f"{bloquee.date_echeance:%d/%m/%Y}, n'est pas "
                    f"entièrement soldée. Elle doit être réglée avant "
                    f"la tranche {tranche.numero}."
                )

        try:
            montant = _valider_montant_paiement(montant_saisi)
        except ValidationError as erreur:
            contexte["erreurs"]["montant"] = erreur.messages[0]
            montant = None

        # La page dediee doit reafficher la tranche choisie apres une
        # erreur : sans cela le select repart vide et l'utilisateur
        # doit tout reselectionner.
        if tranche is not None:
            contexte["tranche"] = tranche
            contexte["reste_tranche"] = _reste_tranche(tranche)

        # =====================================================
        # ENREGISTREMENT
        # =====================================================

        if not contexte["erreurs"] and montant is not None:

            # Le modele impose 0.01 au minimum ; un montant superieur
            # a la tranche ou depassant deux decimales doit etre
            # refuse avant d'atteindre la base.
            reste = _reste_tranche(tranche)
            erreur_modele = {}

            if reste is not None and montant > reste:
                erreur_modele["montant"] = (
                    f"Le montant dépasse le reste à payer sur cette "
                    f"tranche ({reste})."
                )

            if erreur_modele:
                contexte["erreurs"] = erreur_modele
            else:
                with transaction.atomic():
                    paiement = Paiement.objects.create(
                        inscription=inscription,
                        tranche=tranche,
                        montant=montant,
                        enregistre_par=utilisateur,
                        statut=Paiement.ENREGISTRE,
                    )

                    try:
                        paiement.full_clean()
                    except ValidationError as erreur:
                        # Les regles du modele sont le dernier rempart :
                        # on ne veut pas d'un paiement enregistre a moitie.
                        transaction.set_rollback(True)
                        contexte["erreurs"] = {
                            "montant": " ".join(
                                erreur.messages
                            )
                        }
                        paiement = None

                if paiement is not None:
                    message_vers_notification(
                        request,
                        "SUCCESS",
                        f"Paiement de {montant} enregistré pour "
                        f"{inscription.eleve}.",
                        f"Paiement de {montant} enregistré pour "
                        f"{inscription.eleve}.",
                    )

                    contexte["paiement"] = paiement

                    # =========================================
                    # RÉPONSE JSON POUR LA FENÊTRE
                    # =========================================

                    if request.headers.get(
                        "X-Requested-With"
                    ) == "XMLHttpRequest":
                        return JsonResponse({
                            "succes": True,
                            "paiement_id": paiement.id,
                            "montant": str(montant),
                            "message": (
                                f"Paiement de {montant} enregistré."
                            ),
                        })

                    return redirect("liste_paiements")

    # =====================================================
    # AFFICHAGE
    # =====================================================

    # La fenetre de paiement envoie son POST en AJAX et attend du JSON.
    # Sans cette sortie, une erreur de validation rendait la page
    # HTML complete : le parseur JSON du navigateur echouait et
    # l'utilisateur lisait « Erreur reseau » au lieu du motif reel
    # (montant superieur au reste, tranche bloquee, etc.).
    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With")
        == "XMLHttpRequest"
        and contexte["erreurs"]
    ):
        return JsonResponse(
            {
                "succes": False,
                "erreurs": contexte["erreurs"],
                "error": " ".join(contexte["erreurs"].values()),
            },
            status=400,
        )

    if request.GET.get("format") == "fragment":

        # La fenetre demande le formulaire pour une inscription donnee :
        # sans cette lecture, le fragment s'affichait avec un formulaire
        # vide et sans le nom de l'eleve, puisque le POST n'a pas encore
        # eu lieu.
        inscription = (
            Inscription.objects
            .filter(
                id=_id_ou_none(request.GET.get("inscription_id")),
                statut=Inscription.ACTIVE,
            )
            .select_related("eleve", "annee", "classe")
            .first()
        )

        if inscription is not None:
            contexte["inscription"] = inscription

            # L'identifiant repart dans la saisie : sans cela le champ
            # cache rendu par le fragment vautait une chaine vide, et le
            # POST repartait avec inscription_id vide. Le serveur
            # rejetait alors le paiement avec « Selectionnez une
            # inscription active » alors que l'eleve etait justement
            # affiche a l'ecran. On recopie l'identifiant de
            # l'inscription relue, et non celui de la requete : c'est
            # elle qui fait foi.
            contexte["saisie"]["inscription_id"] = inscription.id

        if request.GET.get("tranche_id"):
            contexte["saisie"]["tranche_id"] = request.GET[
                "tranche_id"
            ]

        return render(
            request,
            "comptabilite/formulaire_paiement_modal.html",
            contexte,
        )

    return render(
        request,
        "comptabilite/encaisser_paiement.html",
        contexte,
    )


def _reste_tranche(tranche):
    """Montant restant a solder sur une tranche, paiements valides."""
    from decimal import Decimal

    from .models import Paiement

    if tranche is None:
        return None

    paye = (
        Paiement.objects
        .filter(tranche=tranche, statut=Paiement.VALIDE)
        .aggregate(total=Sum("montant"))["total"]
        or Decimal("0.00")
    )

    return tranche.montant - paye


def ajax_eleves_par_nom(request):
    """Recherche d'eleves par nom, postnom ou prenom.

    Le filtre portrait deux fois sur le nom et jamais sur le postnom :
    le patronyme, qui est le second nom de famille dans ce pays, n'était
    donc jamais cherche.

    La reponse ne renvoie que nom et prenom : deux eleves peuvent porter
    les memes sans etre le meme eleve. Le matricule et la classe
    distinguent les homonymes, et c'est l'utilisateur qui choisit.
    """
    from .models import Eleve

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"results": []})

    requete = (request.GET.get("q") or "").strip()
    if len(requete) < 2:
        return JsonResponse({"results": []})

    classe_id = request.GET.get("classe_id")
    classe = None

    if classe_id:
        classe = Classe.objects.filter(
            id=classe_id, actif=True
        ).first()

    eleves = Eleve.objects.filter(actif=True).filter(
        Q(nom__icontains=requete)
        | Q(postnom__icontains=requete)
        | Q(prenom__icontains=requete)
    )

    # Le filtre par classe porte sur l'inscription en cours, pas sur
    # l'eleve : un eleve reinscrit dans une autre classe existe deux
    # fois, et seule la classe choisie ici doit restreindre la liste.
    inscriptions = Inscription.objects.filter(
        eleve__in=eleves,
        statut=Inscription.ACTIVE,
    )

    if classe is not None:
        inscriptions = inscriptions.filter(classe=classe)

    inscriptions = inscriptions.select_related(
        "eleve", "classe", "annee"
    ).order_by("eleve__nom", "eleve__postnom", "eleve__prenom")

    resultats = []
    vus = set()

    for inscription in inscriptions[:20]:
        eleve = inscription.eleve

        if eleve.id in vus:
            continue

        vus.add(eleve.id)

        nom_complet = " ".join(
            partie
            for partie in (eleve.nom, eleve.postnom, eleve.prenom)
            if partie
        )

        libelle_classe = (
            inscription.classe.libelle
            if inscription.classe_id
            else "—"
        )

        resultats.append({
            "id": eleve.id,
            "text": nom_complet,
            "matricule": eleve.matricule,
            "classe": libelle_classe,
            "annee_id": inscription.annee_id,
            "annee": inscription.annee.libelle,
            "detail": f"{eleve.matricule} — {libelle_classe}",
        })

    return JsonResponse({"results": resultats})


def ajax_classes_par_libelle(request):
    """Classes actives recherchees par libelle, code ou niveau.

    Sert a preselectionner la classe dans la fenetre de paiement : sans
    elle, la liste deroule des classes melangees et le secretariat doit
    deviner laquelle corresponds a la demande.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"results": []})

    requete = (request.GET.get("q") or "").strip()

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    classes = Classe.objects.filter(actif=True).select_related(
        "niveau", "section", "annee"
    )

    if annee_active:
        classes = classes.filter(annee=annee_active)

    if len(requete) >= 2:
        classes = classes.filter(
            Q(libelle__icontains=requete)
            | Q(code__icontains=requete)
            | Q(niveau__libelle__icontains=requete)
        )

    return JsonResponse({
        "results": [
            {
                "id": classe.id,
                "text": classe.libelle,
                "detail": (
                    f"{classe.code} — "
                    f"{classe.niveau.libelle if classe.niveau_id else '—'}"
                ),
            }
            for classe in classes.order_by(
                "niveau__ordre", "code"
            )[:20]
        ]
    })


def ajax_inscriptions_eleve(request, eleve_id):
    """Inscriptions actives d'un eleve (format select2)."""
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"results": []})

    inscriptions = (
        Inscription.objects
        .filter(eleve_id=eleve_id, statut=Inscription.ACTIVE)
        .select_related("annee", "classe")
        .order_by("-annee__libelle")
    )

    return JsonResponse({
        "results": [
            {
                "id": inscription.id,
                "text": (
                    f"{inscription.annee.libelle} — "
                    f"{inscription.classe.libelle if inscription.classe else '—'}"
                ),
                "annee_id": inscription.annee_id,
                "classe_id": inscription.classe_id,
            }
            for inscription in inscriptions
        ]
    })


def ajax_tranches_par_inscription(request, inscription_id):
    """Tranche a solder pour une inscription.

    Une seule tranche est proposee : la premiere echue et non soldee.
    Les tranches suivantes apparaissent apres que celle-ci est
    reglee, dans l'ordre des echeances. Sans cette regle, le menu
    presentait toutes les tranches et la plus ancienne pouvait etre
    sautee au profit de la plus recente.
    """
    from decimal import Decimal

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"results": []})

    inscription = Inscription.objects.filter(
        id=_id_ou_none(inscription_id)
    ).first()
    if not inscription:
        return JsonResponse({"results": []})

    frais_ids = _frais_scolaires_de(inscription)
    if not frais_ids:
        return JsonResponse({"results": []})

    tranche, reste = _tranche_a_solder(frais_ids)

    if tranche is None:
        return JsonResponse({
            "results": [],
            "message": (
                "Toutes les tranches sont soldées."
            ),
        })

    return JsonResponse({
        "results": [
            {
                "id": tranche.id,
                "text": (
                    f"Tranche {tranche.numero} — "
                    f"échéance {tranche.date_echeance:%d/%m/%Y} — "
                    f"reste {reste} / {tranche.montant}"
                ),
                "montant": str(reste),
            }
        ]
    })


def _frais_scolaires_de(inscription):
    """Retourne les ids des frais Scolaires rattaches a une inscription.

    Les frais sont rattaches a l'annee scolaire ; si l'inscription ne porte
    pas d'annee, aucun frais n'est propose.
    """
    from .models import FraisScolaires

    if not inscription.annee_id:
        return []
    return list(
        FraisScolaires.objects
        .filter(annee_id=inscription.annee_id, actif=True)
        .values_list("id", flat=True)
    )


def ajax_inscriptions_par_classe(request, classe_id):
    """Eleves inscrits d'une classe, pour la fenetre de paiement.

    Renvoie l'inscription et non le seul eleve : le paiement porte sur
    une inscription (annee + classe), et c'est elle que la fenetre
    doit transmettre. Deux eleves peuvent par ailleurs porter le meme
    nom, le matricule les distingue.
    """
    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return JsonResponse({"inscriptions": []})

    classe = Classe.objects.filter(id=classe_id, actif=True).first()
    if not classe:
        return JsonResponse({"error": "Classe introuvable"}, status=404)

    inscriptions = (
        Inscription.objects
        .filter(classe=classe, statut=Inscription.ACTIVE)
        .select_related("eleve", "annee")
        .order_by("eleve__nom", "eleve__postnom", "eleve__prenom")
    )

    return JsonResponse({
        "classe": classe.libelle,
        "inscriptions": [
            {
                "id": inscription.id,
                "eleve_id": inscription.eleve_id,
                "matricule": inscription.eleve.matricule,
                "eleve": " ".join(
                    partie
                    for partie in (
                        inscription.eleve.nom,
                        inscription.eleve.postnom,
                        inscription.eleve.prenom,
                    )
                    if partie
                ),
                "annee_id": inscription.annee_id,
                "annee": inscription.annee.libelle,
            }
            for inscription in inscriptions
        ],
    })


def liste_presences(request):
    from .models import Presence

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    classes = Classe.objects.filter(actif=True)
    if annee_active:
        classes = classes.filter(annee=annee_active)
    classes = classes.order_by("niveau__ordre", "code")

    date_str = request.GET.get("date") or timezone.localdate().isoformat()
    try:
        date_presence = date.fromisoformat(date_str)
    except ValueError:
        date_presence = timezone.localdate()
        date_str = date_presence.isoformat()

    classe_id = request.GET.get("classe_id")
    if classe_id:
        classes_filtre = classes.filter(id=classe_id)
    else:
        classes_filtre = classes

    presences = (
        Presence.objects
        .filter(date_presence=date_presence)
        .select_related(
            "inscription", "inscription__eleve", "inscription__classe", "saisi_par"
        )
        .order_by("inscription__classe__code", "inscription__eleve__nom")
    )
    if classe_id:
        presences = presences.filter(inscription__classe_id=classe_id)

    return render(request, "presence/liste.html", {
        "utilisateur": utilisateur,
        "classes": classes_filtre,
        "classe_id": classe_id or "",
        "date_str": date_str,
        "presences": presences,
    })


def presences_classe(request, classe_id):
    from .models import Presence

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    classe = get_object_or_404(
        Classe.objects.select_related("annee", "niveau", "section"),
        id=classe_id,
    )

    date_str = request.GET.get("date") or timezone.localdate().isoformat()
    try:
        date_presence = date.fromisoformat(date_str)
    except ValueError:
        date_presence = timezone.localdate()
        date_str = date_presence.isoformat()

    inscriptions = list(
        Inscription.objects
        .filter(classe=classe, statut=Inscription.ACTIVE)
        .select_related("eleve")
        .order_by("eleve__nom", "eleve__prenom")
    )

    # Une entree par eleve, completee par la presence du jour s'il en existe une
    par_inscription = {
        presence.inscription_id: presence
        for presence in Presence.objects.filter(
            date_presence=date_presence,
            inscription__classe=classe,
        ).select_related("inscription")
    }

    presences = [
        {"inscription": inscription, "presence": par_inscription.get(inscription.id)}
        for inscription in inscriptions
    ]

    return render(request, "presence/classe.html", {
        "utilisateur": utilisateur,
        "classe": classe,
        "date_str": date_str,
        "presences": presences,
    })


def saisir_presences(request, classe_id):
    from .models import Presence

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    classe = get_object_or_404(
        Classe.objects.select_related("annee", "niveau", "section"),
        id=classe_id,
    )

    date_str = request.GET.get("date") or timezone.localdate().isoformat()
    try:
        date_presence = date.fromisoformat(date_str)
    except ValueError:
        date_presence = timezone.localdate()
        date_str = date_presence.isoformat()

    inscriptions = list(
        Inscription.objects
        .filter(classe=classe, statut=Inscription.ACTIVE)
        .select_related("eleve")
        .order_by("eleve__nom", "eleve__prenom")
    )
    par_inscription = {
        presence.inscription_id: presence
        for presence in Presence.objects.filter(
            date_presence=date_presence,
            inscription__classe=classe,
        )
    }

    if request.method == "POST":
        date_str = request.POST.get("date_presence") or date_str
        try:
            date_presence = date.fromisoformat(date_str)
        except ValueError:
            date_presence = timezone.localdate()
            date_str = date_presence.isoformat()

        # Le formulaire renvoie une ligne par eleve, dans l'ordre des ids
        statuts = request.POST.getlist("statut")
        justifications = request.POST.getlist("justification")

        with transaction.atomic():
            for index, inscription in enumerate(inscriptions):
                statut = statuts[index] if index < len(statuts) else Presence.PRESENT
                justification = (
                    justifications[index] if index < len(justifications) else ""
                ).strip()

                Presence.objects.update_or_create(
                    inscription=inscription,
                    horaire_id=_horaire_presence_par_defaut(classe),
                    date_presence=date_presence,
                    defaults={
                        "statut": statut,
                        "justification": justification or None,
                        "saisi_par": utilisateur,
                    },
                )

        message_vers_notification(
            request, "SUCCESS",
            "Appel effectue.",
            "Appel effectue.",
        )
        return redirect(f"{reverse('presences_classe', args=[classe.id])}?date={date_str}")

    eleves_data = [
        {
            "inscription": inscription,
            "statut": getattr(
                par_inscription.get(inscription.id), "statut", Presence.PRESENT
            ),
            "justification": getattr(
                par_inscription.get(inscription.id), "justification", ""
            ),
        }
        for inscription in inscriptions
    ]

    return render(request, "presence/saisie.html", {
        "utilisateur": utilisateur,
        "classe": classe,
        "date_presence": date_presence,
        "eleves_data": eleves_data,
    })


def _horaire_presence_par_defaut(classe):
    """Retourne le premier horaire de la classe, ou None s'il n'y en a pas."""
    return (
        Horaire.objects
        .filter(classe=classe)
        .order_by("jour", "creneau__ordre")
        .values_list("id", flat=True)
        .first()
    )


def justifier_presence(request, presence_id):
    from .models import Presence

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    presence = get_object_or_404(
        Presence.objects.select_related("inscription", "inscription__classe"),
        id=presence_id,
    )

    if request.method == "POST":
        presence.justification = request.POST.get("justification", "").strip() or None
        presence.save(update_fields=["justification"])
        message_vers_notification(
            request, "SUCCESS",
            "Absence justifiee.",
            "Absence justifiee.",
        )
        return redirect(
            f"{reverse('presences_classe', args=[presence.inscription.classe_id])}"
            f"?date={presence.date_presence.isoformat()}"
        )

    return render(request, "presence/justifier.html", {
        "utilisateur": utilisateur,
        "presence": presence,
    })


def administration(request):
    return render(request, "admin/administration.html")


def detail_modele_bulletin(request, pk):
    from .models import ModeleBulletin

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    modele = get_object_or_404(
        ModeleBulletin.objects.select_related("niveau", "section"),
        id=pk,
    )

    return render(request, "admin/detail_modele.html", {
        "titre": f"Modele de bulletin — {modele.libelle}",
        "modele": modele,
    })


def creer_modele_bulletin(request):
    from .forms import ModeleBulletinForm

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    if request.method == "POST":
        form = ModeleBulletinForm(request.POST)
        if form.is_valid():
            form.save()
            message_vers_notification(
                request, "SUCCESS",
                "Modele de bulletin enregistre.",
                "Modele de bulletin enregistre.",
            )
            return redirect("liste_modeles_bulletin")
    else:
        form = ModeleBulletinForm()

    return render(request, "admin/creer_modele_bulletin.html", {"form": form})


def liste_modeles_bulletin(request):
    from .models import ModeleBulletin

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    return render(request, "admin/liste_modeles_bulletins.html", {
        "titre": "Modeles de bulletin",
        "modeles": ModeleBulletin.objects
        .select_related("niveau", "section")
        .order_by("code"),
    })


def liste_ponderations(request):
    from .models import PonderationMatiere

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    niveaux = list(
        Niveau.objects.all().order_by("ordre", "libelle")
    )
    niveau_selectionne = None
    code_niveau = request.GET.get("niveau")
    if code_niveau:
        niveau_selectionne = next(
            (n for n in niveaux if str(getattr(n, "code", "")) == str(code_niveau)),
            None,
        )

    ponderations = (
        PonderationMatiere.objects
        .filter(actif=True)
        .select_related("niveau", "section", "matiere")
        .order_by("niveau__ordre", "matiere__libelle")
    )
    if niveau_selectionne:
        ponderations = ponderations.filter(niveau=niveau_selectionne)

    return render(request, "admin/liste_ponderation.html", {
        "titre": "Liste des pondérations",
        "niveaux": niveaux,
        "niveau": niveau_selectionne,
        "niveau_selectionne": niveau_selectionne,
        "ponderations": ponderations,
    })


def detail_ponderation(request, pk):
    from .models import PonderationMatiere

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    ponderation = get_object_or_404(
        PonderationMatiere.objects
        .select_related("niveau", "section", "matiere"),
        id=pk,
    )

    return render(request, "admin/detail_ponderation.html", {
        "titre": f"Pondération — {ponderation.matiere.libelle}",
        "ponderation": ponderation,
    })


def liste_frais(request):
    from .models import FraisScolaires

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    frais = (
        FraisScolaires.objects
        .select_related("annee")
        .prefetch_related("tranches")
        .order_by("-annee__libelle", "libelle")
    )

    return render(request, "admin/liste_frais.html", {
        "annee_active": annee_active,
        "frais": frais,
    })


def creer_frais(request):
    from .forms import FraisScolairesForm

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    if request.method == "POST":
        form = FraisScolairesForm(request.POST)
        if form.is_valid():
            form.save()
            message_vers_notification(
                request, "SUCCESS",
                "Frais scolaires enregistrés.",
                "Frais scolaires enregistrés.",
            )
            return redirect("liste_frais")
    else:
        form = FraisScolairesForm()

    return render(request, "admin/creer_frais.html", {"form": form})


def liste_tranches(request):
    from .models import Tranche

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    tranches = (
        Tranche.objects
        .select_related("frais", "frais__annee")
        .order_by("frais__libelle", "numero")
    )

    return render(request, "admin/liste_tranches.html", {
        "annee_active": annee_active,
        "tranches": tranches,
    })


def creer_tranche(request):
    from .forms import TrancheForm

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    if request.method == "POST":
        form = TrancheForm(request.POST)
        if form.is_valid():
            form.save()
            message_vers_notification(
                request, "SUCCESS",
                "Tranche enregistrée.",
                "Tranche enregistrée.",
            )
            return redirect("liste_tranches")
    else:
        form = TrancheForm()

    return render(request, "admin/creer_tranche.html", {"form": form})


def configuration_generale(request):
    from .models import FraisScolaires

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    annee_active = AnneeScolaire.objects.filter(
        statut=AnneeScolaire.ACTIVE
    ).first()

    return render(request, "admin/configuration_generale.html", {
        "annee_active": annee_active,
        "frais": FraisScolaires.objects.select_related("annee").order_by("-annee__libelle"),
    })


def bulletin_officiel(request, pk):
    from .models import Bulletin

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    bulletin = get_object_or_404(
        Bulletin.objects
        .select_related("annee_scolaire", "inscription__eleve", "inscription__classe"),
        id=pk,
    )

    contexte = _contexte_bulletin(bulletin)
    contexte["utilisateur"] = utilisateur
    return render(request, "admin/bulletin_officiel.html", contexte)


def bulletin_impression(request, pk):
    from .models import Bulletin

    utilisateur = _utilisateur_courant(request)
    if not utilisateur:
        return redirect("connexion")

    bulletin = get_object_or_404(
        Bulletin.objects
        .select_related("annee_scolaire", "inscription__eleve", "inscription__classe"),
        id=pk,
    )

    contexte = _contexte_bulletin(bulletin)
    contexte["utilisateur"] = utilisateur
    return render(request, "admin/bulletin_impression.html", contexte)
