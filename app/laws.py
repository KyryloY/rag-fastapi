LAW_ABBREVIATIONS: tuple[str, ...] = (
    "ArbZG",
    "BUrlG",
    "KSchG",
    "TzBfG",
    "EntgFG",
    "NachwG",
    "MiLoG",
    "AGG",
    "MuSchG",
    "JArbSchG",
    "BEEG",
    "ArbSchG",
)

# Folder names on gesetze-im-internet.de when they differ from lowercased abbreviations.
_LAW_SLUGS: dict[str, str] = {
    "MuSchG": "muschg_2018",
}


def law_xml_slug(abbreviation: str) -> str:
    return _LAW_SLUGS.get(abbreviation, abbreviation.lower())
