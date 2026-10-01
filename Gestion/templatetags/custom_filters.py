from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Permet d'accéder à une valeur de dictionnaire avec une clé variable dans les templates Django.
    Usage: {{ mon_dict|get_item:ma_cle }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.simple_tag
def cours_cellule(horaires, creneau_id, jour):
    """Cours place dans la grille au couple (jour, creneau).

    Usage: {% cours_cellule horaires creneau.id 1 as cours %}
    """
    if not isinstance(horaires, dict):
        return None
    return horaires.get((jour, creneau_id))