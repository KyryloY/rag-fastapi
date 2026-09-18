from app.chat import ChatClient, ChatResult
from app.parse_xml import Chunk

SYSTEM_PROMPT = """You answer questions using only the statute excerpts in the user message.
Reply in the same language as the question.
If the excerpts are insufficient, say that the loaded documents do not contain the answer.
Do not invent figures, company facts, or legal results.
Do not invent citations.
Return JSON only with keys "answer" (string) and "refused" (boolean).
Set refused to true only when the excerpts do not contain the answer.
"""


def build_user_prompt(question: str, chunks: list[Chunk]) -> str:
    parts = [f"Question: {question}", "", "Excerpts:"]
    for chunk in chunks:
        parts.append(f"Locator: {chunk.locator}")
        parts.append(f"Text: {chunk.text}")
        parts.append("")
    return "\n".join(parts).strip()


def answer_question(question: str, chunks: list[Chunk], chat_client: ChatClient) -> ChatResult:
    return chat_client.complete(SYSTEM_PROMPT, build_user_prompt(question, chunks))
