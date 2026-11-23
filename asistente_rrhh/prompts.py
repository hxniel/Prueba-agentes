from asistente_rrhh import config


def cargar_prompt(nombre: str) -> str:
    """Lee el system prompt prompts/<nombre>.md y rechaza los que contienen llaves.

    Args:
        nombre: Nombre del prompt sin extensión.
    """
    texto = (config.RAIZ / "prompts" / f"{nombre}.md").read_text(encoding="utf-8")
    if "{" in texto or "}" in texto:
        raise ValueError(f"El prompt {nombre} contiene llaves.")
    return texto
