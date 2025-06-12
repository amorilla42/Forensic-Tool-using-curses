import io
import contextlib
from impacket.examples.secretsdump import LocalOperations, SAMHashes

def extraer_usuarios(system_path, sam_path):
    local_ops = LocalOperations(system_path)
    bootkey = local_ops.getBootKey()
    sam_hashes = SAMHashes(sam_path, bootkey, isRemote=False)

    with contextlib.redirect_stdout(io.StringIO()):
        sam_hashes.dump()

    resultado = []
    raw_items = sam_hashes._SAMHashes__itemsFound

    for rid, entry in raw_items.items():
        try:
            partes = entry.strip().split(":")
            if len(partes) >= 4:
                username, rid_str, lm_hash, nt_hash = partes[:4]
                resultado.append({
                    "username": username,
                    "rid": int(rid_str),
                    "lm_hash": lm_hash,
                    "nt_hash": nt_hash
                })
        except Exception as e:
            pass

    sam_hashes.finish()
    return resultado


def buscar_usuario_por_rid(lista_usuarios, rid_buscado):
    for usuario in lista_usuarios:
        if usuario["rid"] == rid_buscado:
            return usuario
    return None



