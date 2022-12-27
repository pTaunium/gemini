from typing import AsyncGenerator


async def stream_reader(
    stream: AsyncGenerator[bytes, None], chunk_size: int = 128,
) -> AsyncGenerator[bytes, None]:
    body = b""
    async for chunk in stream:
        body += chunk
        while len(body) >= chunk_size:
            yield body[:chunk_size]
            body = body[chunk_size:]

    if len(body) > 0:
        yield body
