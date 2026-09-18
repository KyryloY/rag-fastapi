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


_ABSATZ_SPLIT_RE = re.compile(r"(?m)(?=^\(\d+\))")
_ABSATZ_PREFIX_RE = re.compile(r"^\((\d+)\)")


def _window_text(
    text: str, max_chars: int, overlap: int
) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        parts.append(text[start : start + max_chars])
        if start + max_chars >= len(text):
            break
        start += max_chars - overlap
    return parts


def _split_chunk_by_absatz(chunk: Chunk, max_chars: int, overlap: int) -> list[Chunk] | None:
    raw_parts = [p for p in _ABSATZ_SPLIT_RE.split(chunk.text) if p]
    if len(raw_parts) < 2:
        return None

    absatz_items: list[tuple[str, str]] = []
    for part in raw_parts:
        match = _ABSATZ_PREFIX_RE.match(part.lstrip())
        if not match:
            return None
        absatz_items.append((match.group(1), part))

    result: list[Chunk] = []
    oversized = [text for _, text in absatz_items if len(text) > max_chars]
    for n, part_text in absatz_items:
        if len(part_text) > max_chars:
            if len(oversized) == 1:
                windows = _window_text(part_text, max_chars, overlap)
                for i, window in enumerate(windows, start=1):
                    result.append(
                        Chunk(
                            law=chunk.law,
                            paragraph=chunk.paragraph,
                            locator=f"{chunk.law} § {chunk.paragraph} (part {i})",
                            title=chunk.title,
                            text=window,
                        )
                    )
            else:
                result.append(
                    Chunk(
                        law=chunk.law,
                        paragraph=chunk.paragraph,
                        locator=f"{chunk.law} § {chunk.paragraph} Abs. {n}",
                        title=chunk.title,
                        text=part_text,
                    )
                )
        else:
            result.append(
                Chunk(
                    law=chunk.law,
                    paragraph=chunk.paragraph,
                    locator=f"{chunk.law} § {chunk.paragraph} Abs. {n}",
                    title=chunk.title,
                    text=part_text,
                )
            )
    return result


def split_chunks(
    chunks: list[Chunk], max_chars: int = 6000, overlap: int = 200
) -> list[Chunk]:
    result: list[Chunk] = []
    for chunk in chunks:
        if len(chunk.text) <= max_chars:
            result.append(chunk)
            continue

        absatz_split = _split_chunk_by_absatz(chunk, max_chars, overlap)
        if absatz_split is not None:
            result.extend(absatz_split)
            continue

        windows = _window_text(chunk.text, max_chars, overlap)
        for i, window in enumerate(windows, start=1):
            result.append(
                Chunk(
                    law=chunk.law,
                    paragraph=chunk.paragraph,
                    locator=f"{chunk.law} § {chunk.paragraph} (part {i})",
                    title=chunk.title,
                    text=window,
                )
            )
    return result
