from django.urls import path

from . import views 


urlpatterns = [
    #AUTHENTIFICATION
    path("", views.connexion, name="connexion" ),
    path( "deconnexion/",views.deconnexion,name="deconnexion" ),
    path("changer-mot-de-passe/",views.changer_mot_de_passe, name="changer_mot_de_passe" ),
    path("mon-profil/", views.mon_profil, name="mon_profil"),
    path("acces-refuse/",views.acces_refuse,name="acces_refuse"),
    
    #TABLEAU DE BORD
    path("dashboard/",views.dashboard_admin,name="dashboard_admin"),
    path("promoteur/",views.dashboard_promoteur,name="dashboard_promoteur"),
    path("directeur/",views.dashboard_directeur, name="dashboard_directeur"),
    path("prefet/",views.dashboard_prefet,name="dashboard_prefet"),
    path("comptabilite/",views.dashboard_comptabilite,name="dashboard_comptabilite"),
    path("caisse/",views.dashboard_caisse,name="dashboard_caisse"),
    path("secretaire/",views.dashboard_secretaire,name="dashboard_secretaire"),
    path("enseignant/",views.dashboard_enseignant,name="dashboard_enseignant"),
    path("discipline/",views.dashboard_discipline,name="dashboard_discipline"),
    
    # =========================================================
    # INTERFACE ENSEIGNANT
    # =========================================================
    path("enseignant/mes-affectations/",views.mes_affectations,name="mes_affectations"),
    path("enseignant/mes-evaluations/",views.mes_evaluations,name="mes_evaluations"),
    path("enseignant/saisie-notes/<int:evaluation_id>/",views.saisie_notes,name="saisie_notes"),
    path("enseignant/mes-eleves/",views.mes_eleves,name="mes_eleves"),
    path("enseignant/ma-classe/", views.ma_classe, name="ma_classe"),
    path("enseignant/titularisation/creer/", views.creer_titularisation, name="creer_titularisation"),
    path("ajax/options-titularisation/", views.ajax_options_titularisation, name="ajax_options_titularisation"),
    path("eleves/",views.liste_eleves,name="liste_eleves"),
    path("eleves/tous/", views.liste_tous_eleves, name="liste_tous_eleves"),
    path("eleves/<int:eleve_id>/",views.detail_eleve,name="detail_eleve"),
    path("eleves/<int:eleve_id>/modifier/",views.modifier_eleve,name="modifier_eleve"),
    path("eleves/<int:eleve_id>/carte/",views.carte_eleve,name="carte_eleve"),
    path("enseignants/<int:enseignant_id>/carte-service/", views.carte_service_enseignant, name="carte_service_enseignant"),
    path("eleves/<int:eleve_id>/bulletin/", views.bulletin_eleve, name="bulletin_eleve"),
    path("eleves/classe/<int:classe_id>/",views.eleves_par_classe,name="eleves_par_classe"),
    path("eleves/classe/<int:classe_id>/pdf/",views.eleves_par_classe_pdf,name="eleves_par_classe_pdf"),
    path("eleves/creer/",views.creer_eleve,name="creer_eleve"),
    path("eleves/reinscription/",views.reinscription,name="reinscription"),
    path("enseignant/emploi-du-temps/",views.emploi_du_temps,name="emploi_du_temps"),
    
    #UTILISATEUR
    path("Gestionutilisateur/",views.liste_utilisateurs,name="liste_utilisateurs"),
    path("Gestion/nouveau/",views.creer_utilisateur,name="creer_utilisateur"),
    path("utilisateurs/<int:utilisateur_id>/modifier/",views.modifier_utilisateur,name="modifier_utilisateur",),
    path("utilisateurs/<int:utilisateur_id>/activer-desactiver/",views.desactiver_utilisateur,name="desactiver_utilisateur"),
    path("utilisateurs/<int:utilisateur_id>/",views.detail_utilisateur,name="detail_utilisateur"),
    path("utilisateurs/<int:utilisateur_id>/reinitialiser-mot-de-passe/",views.reinitialiser_mot_de_passe,name="reinitialiser_mot_de_passe",),
    path("utilisateurs/<int:utilisateur_id>/activites/",views.activites_utilisateur,name="activites_utilisateur",),
    
    # ============================================================
    # ANNÃ‰ES SCOLAIRES
    # ============================================================
    path("annee/structure-academique/",views.structure_academique,name="structure_academique",),
    path("annee/annees/",views.liste_annees,name="liste_annees"),
    path("annee/annees/nouvelle/",views.creer_annee,name="creer_annee"),
    path("annee/annees/<int:annee_id>/",views.detail_annee,name="detail_annee",),
    path("annee/annees/<int:annee_id>/modifier/",views.modifier_annee,name="modifier_annee",),
    path("annee/annees/<int:annee_id>/activer/", views.activer_annee,name="activer_annee",),
    path("annee/annees/<int:annee_id>/cloturer/",views.cloturer_annee,name="cloturer_annee",),
    
    #=========================================================
    #SECTIONS
    #=========================================================
    path("annee/sections/",views.liste_sections,name="liste_sections",),
    path("annee/sections/nouvelle/",views.creer_section,name="creer_section",),
    path("annee/sections/<int:section_id>/",views.detail_section,name="detail_section",),
    path("annee/sections/<int:section_id>/modifier/",views.modifier_section,name="modifier_section",),
    path("annee/sections/<int:section_id>/activer-desactiver/",views.activer_desactiver_section,name="activer_desactiver_section",),

    #========================================================
    #NIVEAU
    #========================================================
    path("annee/niveaux/",views.liste_niveaux,name="liste_niveaux",),
    path("annee/niveaux/nouveau/",views.creer_niveau,name="creer_niveau",),
    path("annee/niveaux/<int:niveau_id>/",views.detail_niveau,name="detail_niveau",),
    path("annee/niveaux/<int:niveau_id>/modifier/",views.modifier_niveau,name="modifier_niveau",),
    path("annee/niveaux/<int:niveau_id>/statut/",views.activer_desactiver_niveau,name="activer_desactiver_niveau",),
    
    #===========================================================
    #CLASSES
    #===========================================================
    path("annee/classes/",views.liste_classes,name="liste_classes",),
    path("annee/classes/nouvelle/",views.creer_classe,name="creer_classe",),
    path("annee/classes/<int:classe_id>/",views.detail_classe,name="detail_classe",),
    path("annee/classes/<int:classe_id>/modifier/",views.modifier_classe,name="modifier_classe",),
    path("annee/classes/<int:classe_id>/statut/",views.activer_desactiver_classe,name="activer_desactiver_classe",),
    
    #===========================================================
    #MATIERES
    #============================================================
    path("annee/matieres/",views.liste_matieres,name="liste_matieres",),
    path("annee/matieres/nouvelle/",views.creer_matiere,name="creer_matiere",),
    path("annee/matieres/<int:matiere_id>/",views.detail_matiere,name="detail_matiere",),
    path("annee/matieres/<int:matiere_id>/modifier/",views.modifier_matiere,name="modifier_matiere",),
    path("annee/matieres/<int:matiere_id>/statut/",views.activer_desactiver_matiere,name="activer_desactiver_matiere",),
    
    # ============================================================
    # AFFECTATION DES MATIÃˆRES
    # ============================================================
    path("Gestion/affectations-matieres/",views.liste_affectations_matieres,name="liste_affectations_matieres",),
    path("matieres/gestion/", views.gestion_matieres_classes, name="gestion_matieres_classes"),
    path("matieres/gestion/<int:classe_id>/liste/", views.liste_matieres_classe, name="liste_matieres_classe"),
    path("ajax/horaire-classe/<int:classe_id>/", views.ajax_horaire_classe, name="ajax_horaire_classe"),
    path("Gestion/affectations-matieres/nouvelle/", views.creer_affectation_matiere, name="creer_affectation_matiere"),
    path("annee/affectations-matieres/<int:affectation_id>/",views.detail_affectation_matiere,name="detail_affectation_matiere",),
    path("annee/affectations-matieres/<int:affectation_id>/modifier/",views.modifier_affectation_matiere,name="modifier_affectation_matiere",),
    path("annee/affectations-matieres/<int:affectation_id>/statut/",views.activer_desactiver_affectation_matiere,name="activer_desactiver_affectation_matiere",),

    # ============================================================
    # GESTION DES ENSEIGNANTS
    # ============================================================
    path("enseignants/",views.liste_enseignants,name="liste_enseignants",),
    path("enseignants/nouveau/",views.creer_enseignant,name="creer_enseignant",),
    path("enseignants/<int:enseignant_id>/",views.detail_enseignant,name="detail_enseignant",),
    path("enseignants/<int:enseignant_id>/modifier/",views.modifier_enseignant,name="modifier_enseignant",),
    path("enseignants/<int:enseignant_id>/statut/",views.activer_desactiver_enseignant,name="activer_desactiver_enseignant",),
    
    #==============================================================
    #AFFECTATIONS DES ENSEINGANTS
    #==============================================================
    path("affectations/",views.liste_affectations,name="liste_affectations",),
    path("affectations/cards/",views.gestion_affectations_enseignants,name="gestion_affectations_enseignants",),
    path("affectations/creer/",views.creer_affectation,name="creer_affectation",),
    path("affectations/<int:affectation_id>/",views.detail_affectation,name="detail_affectation",),
    path("affectations/<int:affectation_id>/modifier/",views.modifier_affectation,name="modifier_affectation",),
     path("affectations/<int:affectation_id>/statut/",views.activer_desactiver_affectation,name="activer_desactiver_affectation",),
    
    # ============================================================
    # NOTIFICATIONS
    # ============================================================
    path("notifications/",views.liste_notifications,name="liste_notifications",),
    path("notifications/lue/<int:destinataire_id>/",views.marquer_notification_lue,name="marquer_notification_lue",),
    path("notifications/ajax-recentes/",views.ajax_notifications_recentes,name="ajax_notifications_recentes",),
    
    #============================================================
    #AJAX POUR LES AFFICHAGES
    #=============================================================
    path("ajax/classes-par-annee/",views.ajax_classes_par_annee,name="ajax_classes_par_annee",),
    path("ajax/matieres-disponibles-par-classe/",views.ajax_matieres_disponibles_par_classe,name="ajax_matieres_disponibles_par_classe",),
    path("ajax/matieres-affectees-par-classe/",views.ajax_matieres_affectees_par_classe,name="ajax_matieres_affectees_par_classe",),
    path("ajax/matieres-par-classe/",views.ajax_matieres_par_classe,name="ajax_matieres_par_classe",),
    path("ajax/creneaux-disponibles/",views.ajax_creneaux_disponibles,name="ajax_creneaux_disponibles",),
    path("ajax/matieres-programmation/",views.ajax_matieres_programmation,name="ajax_matieres_programmation",),
    path("ajax/creneaux-programmation/",views.ajax_creneaux_programmation,name="ajax_creneaux_programmation",),

    # =========================================================
    # INTERFACE PRINCIPALE DES ENSEIGNANTS
    # =========================================================
    path("enseignants/gestion/",views.interface_enseignants,name="interface_enseignants"),
        
    # =========================================================
    # ORGANISATION SCOLAIRE
    # =========================================================
    path("organisation-scolaire/",views.interface_organisation_scolaire,name="interface_organisation_scolaire",),
    path("organisation/configuration-journee/",views.configuration_journee,name="configuration_journee",),
    path("organisation/configuration-journee/<int:configuration_id>/generer-creneaux/",views.generer_creneaux,name="generer_creneaux",),
    path("configuration-journee/<int:configuration_id>/valider/",views.valider_configuration_horaire,name="valider_configuration_horaire",),
    path("organisation/repartition-horaire/",views.repartition_horaire,name="repartition_horaire",),
    path("repartition-horaire/<int:annee_id>/<int:classe_id>/<int:creneau_id>/<int:jour>/affecter/",views.affecter_cours,name="affecter_cours",),
    path("repartition-horaire/<int:horaire_id>/supprimer/", views.supprimer_horaire, name="supprimer_horaire"),
    
    path("repartition-horaire/creer/",views.creer_repartition_horaire,name="creer_repartition_horaire",),
    path("repartition-horaire/tableau-bord/",views.tableau_bord_repartition_horaire,name="tableau_bord_repartition_horaire",),
    path("repartition-horaire/liste/",views.liste_repartition_horaire,name="liste_repartition_horaire",),
    path("organisation/calendrier-scolaire/",views.calendrier_scolaire,name="calendrier_scolaire",),
    path("organisation/session-scolaire/",views.session_scolaire,name="session_scolaire",),
    path("organisation/parcours/",views.parcours_scolaire,name="parcours_scolaire",),

    path("inscriptions/", views.liste_inscriptions, name="liste_inscriptions"),
    path("inscriptions/creer/", views.creer_inscription, name="creer_inscription"),
    path("eleves-inscriptions/", views.accueil_eleves_inscriptions, name="accueil_eleves_inscriptions"),

    # =========================================================
    # MODULE COMPTABILITÉ / CAISSE / FINANCES
    # =========================================================
    path("finances/", views.accueil_finances, name="accueil_finances"),

    # =========================================================
    # MODULE COMPTABILITÉ / CAISSE
    # =========================================================
    path("comptabilite/paiements/", views.liste_paiements, name="liste_paiements"),
    path("comptabilite/paiements/<int:paiement_id>/", views.detail_paiement, name="detail_paiement"),
    path("comptabilite/recus/", views.liste_recus, name="liste_recus"),
    path("comptabilite/caisse/<int:caisse_id>/", views.detail_caisse, name="detail_caisse"),
    path("comptabilite/classes/", views.liste_classes_paiements, name="liste_classes_paiements"),
    path("comptabilite/classes/<int:classe_id>/", views.eleves_classe_paiements, name="eleves_classe_paiements"),
    path("comptabilite/encaisser/", views.encaisser_paiement, name="encaisser_paiement"),
    path("ajax/eleves-par-nom/", views.ajax_eleves_par_nom, name="ajax_eleves_par_nom"),
    path("ajax/inscriptions-eleve/<int:eleve_id>/", views.ajax_inscriptions_eleve, name="ajax_inscriptions_eleve"),
    path("ajax/tranches-par-inscription/<int:inscription_id>/", views.ajax_tranches_par_inscription, name="ajax_tranches_par_inscription"),

    # =========================================================
    # MODULE PRÉSENCES
    # =========================================================
    path("presences/", views.liste_presences, name="liste_presences"),
    path("presences/classe/<int:classe_id>/", views.presences_classe, name="presences_classe"),
    path("presences/saisir/<int:classe_id>/", views.saisir_presences, name="saisir_presences"),
    path("presences/justifier/<int:presence_id>/", views.justifier_presence, name="justifier_presence"),
    path("ajax/inscriptions-par-classe/<int:classe_id>/", views.ajax_inscriptions_par_classe, name="ajax_inscriptions_par_classe"),

    path("administration/", views.administration, name="administration"),
    path("configuration-generale/", views.configuration_generale, name="configuration_generale"),
    path("finances/frais/", views.liste_frais, name="liste_frais"),
    path("finances/frais/creer/", views.creer_frais, name="creer_frais"),
    path("finances/tranches/", views.liste_tranches, name="liste_tranches"),
    path("finances/tranches/creer/", views.creer_tranche, name="creer_tranche"),
    path("bulletins/modeles/", views.liste_modeles_bulletin, name="liste_modeles_bulletins"),
    path("bulletins/modeles/creer/", views.creer_modele_bulletin, name="creer_modele_bulletin"),

    # ========================================================
    # BULLETINS
    # ========================================================

    path("bulletins/modeles/",views.liste_modeles_bulletin,name="liste_modeles_bulletin"),
    path("bulletins/modeles/<int:pk>/",views.detail_modele_bulletin,name="detail_modele_bulletin"),
    # PONDERATIONS
    path("bulletins/ponderations/",views.liste_ponderations,name="liste_ponderations"),
    path("bulletins/ponderations/<int:pk>/",views.detail_ponderation,name="detail_ponderation"),
    #bulletins propres
    path("bulletins/<int:pk>/officiel/",views.bulletin_officiel,name="bulletin_officiel",),
    path("bulletins/<int:pk>/impression/",views.bulletin_impression,name="bulletin_impression",),

]
