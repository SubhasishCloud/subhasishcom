import httpx

async def get_graph_link(text, title="Subhasish Encoder Mediainfo", author="Subhasish Encoder"):
    async with httpx.AsyncClient() as client:
        payload = {
            "title": title, 
            "author_name": author,
            "content": [{"tag": "pre", "children": [text]}], 
            "return_content": True
        }
        try:
            # Oracle is in the US, so it can reach the API.
            r = await client.post("https://api.telegra.ph/createPage", json=payload)
            url = r.json().get("result", {}).get("url", "")
            
            # Change the domain to graph.org for Indian users
            return url.replace("telegra.ph", "graph.org")
        except:
            return "Failed to connect to Telegraph API."