import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_PARAGRAPH_RE = re.compile(r"^§\s*([0-9]+[a-z]?)", re.IGNORECASE)


def _local_name(tag: str) -> str:
    return tag.split("}")[-1]


def _child_text(parent: ET.Element, name: str) -> str:
    for child in parent:
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class Chunk:
    law: str
    paragraph: str
    locator: str
    title: str
    text: str


def parse_law_xml(xml_text: str, law_fallback: str) -> list[Chunk]:
    root = ET.fromstring(xml_text)
    chunks: list[Chunk] = []

    for norm in root.iter():
        if _local_name(norm.tag) != "norm":
            continue

        metadaten = next(
            (c for c in norm if _local_name(c.tag) == "metadaten"), None
        )
        textdaten = next(
            (c for c in norm if _local_name(c.tag) == "textdaten"), None
        )
        if metadaten is None or textdaten is None:
            continue

        law = _child_text(metadaten, "jurabk") or law_fallback
        enbez = _child_text(metadaten, "enbez")
        match = _PARAGRAPH_RE.match(enbez)
        if not match:
            continue

        paragraph = match.group(1)
        title = _child_text(metadaten, "titel")
        text = _collapse_whitespace("".join(textdaten.itertext()))
        if not text:
            continue

        chunks.append(
            Chunk(
                law=law,
                paragraph=paragraph,
                locator=f"{law} § {paragraph}",
                title=title,
                text=text,
            )
        )

    return chunks
