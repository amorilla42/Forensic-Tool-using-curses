import re

class TextSanitizer:
    # Caracteres imprimibles típicos (ASCII visibles + espacio)
    _printable_regex = re.compile(r'[^\x20-\x7E]')

    @staticmethod
    def clean(text):
        """
        Limpia una línea de texto para que sea segura de mostrar en curses.
        - Convierte a str.
        - Reemplaza caracteres nulos y no imprimibles por '�'.
        """
        try:
            s = str(text).replace('\x00', '')
        except Exception:
            s = "�"
        return TextSanitizer._printable_regex.sub('�', s)
