import asyncio
import httpx

GRAPH_TOKEN = None

async def get_graph_link(content_json, title="MediaInfo", author="Subhasish Encoder"):
    global GRAPH_TOKEN

    timeout = httpx.Timeout(20)
    limits = httpx.Limits(max_connections=5, max_keepalive_connections=2)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        for attempt in range(3):
            try:
                if not GRAPH_TOKEN:
                    r = await client.get("https://api.telegra.ph/createAccount?short_name=subhasish")
                    r.raise_for_status()
                    GRAPH_TOKEN = r.json()["result"]["access_token"]

                payload = {
                    "access_token": GRAPH_TOKEN,
                    "title": title,
                    "author_name": author,
                    "content": content_json
                }

                r = await client.post("https://api.telegra.ph/createPage", json=payload)
                r.raise_for_status()
                original_url = r.json()["result"]["url"]
                return original_url.replace("telegra.ph", "graph.org")
            except Exception as e:
                if attempt == 2:
                    telegraph_err = f"Telegraph API Connection Error: {e}"
                    raise Exception(telegraph_err)
                await asyncio.sleep(2)
    return None
