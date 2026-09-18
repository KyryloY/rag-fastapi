from io import BytesIO
import sys
import zipfile
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.config import Settings
from app.embeddings import EmbeddingClient, GeminiEmbeddingClient
from app.laws import LAW_ABBREVIATIONS, law_xml_slug
from app.parse_xml import parse_law_xml, split_chunks
from app.retrieve import collection_stats, open_collection, replace_chunks


def download_law_xml(abbreviation: str, http: httpx.Client) -> str:
    slug = law_xml_slug(abbreviation)
    url = f"https://www.gesetze-im-internet.de/{slug}/xml.zip"
    response = http.get(url)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to ingest {abbreviation}: HTTP {response.status_code}"
        )
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        xml_names = [name for name in archive.namelist() if name.lower().endswith(".xml")]
        if not xml_names:
            raise RuntimeError(f"Failed to ingest {abbreviation}: zip has no XML")
        return archive.read(xml_names[0]).decode("utf-8")


def ingest_all(
    abbreviations: tuple[str, ...],
    http: httpx.Client,
    embedding_client: EmbeddingClient | None,
    chroma_path: Path,
) -> None:
    chunks = []
    for abbreviation in abbreviations:
        try:
            xml_text = download_law_xml(abbreviation, http)
            parsed = parse_law_xml(xml_text, abbreviation)
            law_chunks = split_chunks(parsed)
            if not law_chunks:
                raise RuntimeError(
                    f"Failed to ingest {abbreviation}: parsed to zero chunks"
                )
            chunks.extend(law_chunks)
        except Exception as exc:
            message = str(exc)
            if "Failed to ingest" not in message:
                message = f"Failed to ingest {abbreviation}: {exc}"
            print(message, file=sys.stderr)
            raise SystemExit(1) from exc
    collection = open_collection(chroma_path, embedding_client)
    replace_chunks(collection, chunks, embedding_client)
    stats = collection_stats(collection)
    print(f"laws={stats.laws} chunks={stats.chunks} characters={stats.characters}")


def main() -> None:
    load_dotenv()
    settings = Settings()
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is missing", file=sys.stderr)
        raise SystemExit(1)
    with httpx.Client(timeout=60, follow_redirects=True) as http:
        ingest_all(
            LAW_ABBREVIATIONS,
            http,
            GeminiEmbeddingClient(settings),
            settings.chroma_path,
        )


if __name__ == "__main__":
    main()
