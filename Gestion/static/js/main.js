document.addEventListener("DOMContentLoaded", function () {

    const PROFILE_SELECTORS = ".user-avatar, .profile-photo, .teacher-photo, .enseignant-photo, .photo-profil";

    // Préfixe statique réel, déduit du logo rendu par le template.
    function staticPrefix() {
        const logo = document.querySelector("img.institution-logo");

        if (!logo) {
            return "/static/";
        }

        const index = logo.src.indexOf("images/");

        return index === -1 ? "/static/" : logo.src.slice(0, index);

    }

    // Photo de profil absente ou introuvable : avatar générique.
    document.querySelectorAll("img").forEach(function (img) {
        if (!img.matches(PROFILE_SELECTORS)) {
            return;
        }

        img.addEventListener("error", function () {
            if (img.dataset.fallbackApplied === "1") {
                return;
            }

            img.dataset.fallbackApplied = "1";
            img.src = staticPrefix() + "images/default-avatar.svg";
        });
    });

    // Repli si la page ne définit pas toggleSidebar() elle-même.
    if (typeof window.toggleSidebar !== "function") {
        window.toggleSidebar = function () {
            const menu = document.querySelector(".main-menu");

            if (menu) {
                menu.classList.toggle("open");
            }

        };

    }

    // Fermeture du menu et des sous-menus mobiles lors d'un clic à
    // l'extérieur. Le bouton hamburger et le menu lui-même sont exclus :
    // sans cela le clic qui vient d'ouvrir le menu le refermerait aussitôt.
    document.addEventListener("click", function (e) {
        if (window.innerWidth > 768) {
            return;
        }

        if (e.target.closest(".main-menu, .hamburger")) {
            return;
        }

        document.querySelectorAll(".main-menu li.open").forEach(function (li) {
            li.classList.remove("open");
        });

        const menu = document.querySelector(".main-menu");

        if (menu) {
            menu.classList.remove("open");
        }

    });

});