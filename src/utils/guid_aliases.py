import re

# Diccionario con GUIDs conocidos y su alias legible
KNOWN_GUIDS = {
    "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}": "System32",
    "{6D809377-6AF0-444B-8957-A3773F02200E}": "Program Files",
    "{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}": "ProgramData",
    "{0139D44E-6AFE-49F2-8690-3DAFCAE6FFB8}": "Menú Inicio",
    "{9E3995AB-1F9C-4F13-B827-48B24B6C7174}": "Barra de tareas",
    "{F38BF404-1D43-42F2-9305-67DE0B28FC23}": "Windows",
    "{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}": "Accesibilidad",
    "{D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27}": "Herramientas del sistema",
    "{ED228FDF-9EA8-4870-83B1-96B02CFE0D52}": "Menú Inicio\\Programas"
    # Añade más aquí conforme aparezcan nuevos GUIDs en tus casos
}

def traducir_guids(texto):
    """
    Reemplaza GUIDs conocidos por sus alias legibles.
    Si hay GUIDs no reconocidos, los deja tal cual.
    """
    for guid, alias in KNOWN_GUIDS.items():
        texto = texto.replace(guid, alias)
    return texto
