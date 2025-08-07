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
    "{ED228FDF-9EA8-4870-83B1-96B02CFE0D52}": "Menú Inicio\\Programas",
    
    "{c53e7d10-8577-11e3-95e8-806e6f6e6963}": "Unidad optica - LG DVDRAM GSA-4167B (IDE)",
    "{f10825bd-8cca-11e3-9027-001641e7bb6b}": "USB - Kingston DataTraveler 2.0",
    "{f10825c7-8cca-11e3-9027-001641e7bb6b}": "Unidad cifrada - TrueCryptVolumeZ",


    "{f8b55c0f-85c7-11e3-81d3-001641e7bb6b}": "Disco extraíble Kingston",
    "{1b767710-5247-4401-a203-e9dcdc672703}": "Disco USB SanDisk",
    "{be75b00d-0b19-481d-8d0d-52efc6588d22}": "Unidad externa WD"
    
    
}

def traducir_guids(texto):
    """
    Reemplaza GUIDs conocidos por sus alias legibles.
    Si hay GUIDs no reconocidos, los deja tal cual.
    """
    for guid, alias in KNOWN_GUIDS.items():
        texto = texto.replace(guid, alias)
    return texto
