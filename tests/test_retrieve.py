from pathlib import Path

from tests.conftest import KeywordEmbeddingClient, leave_chunk, wage_chunk
from app.retrieve import collection_stats, open_collection, query_chunks, replace_chunks


def test_leave_question_ranks_leave_chunk_first(tmp_path: Path):
    client = KeywordEmbeddingClient()
    collection = open_collection(tmp_path / "chroma", client)
    replace_chunks(collection, [wage_chunk(), leave_chunk()], client)
    hits = query_chunks(collection, "Wie viele Urlaubstage stehen gesetzlich mindestens zu?", client, k=5)
    assert hits[0].locator == "BUrlG § 3"
    stats = collection_stats(collection)
    assert stats.chunks == 2
    assert stats.laws == 2
    assert stats.characters == len(wage_chunk().text) + len(leave_chunk().text)
    assert stats.collection == "labour_law"
