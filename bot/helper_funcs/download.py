import httpx

async def get_graph_link(text, title="Subhasish Encoder Mediainfo", author="Subhasish Encoder"):
    async with httpx.AsyncClient() as client:
        try:
            # 1. Create a dynamic Telegraph Account to get an authorized Access Token
            acc_resp = await client.get("https://api.telegra.ph/createAccount?short_name=SubhasishEncoder&author_name=Subhasish")
            token = acc_resp.json().get("result", {}).get("access_token")
            
            if not token:
                return "❌ Failed to generate Telegraph Token."
                
            # 2. Create the actual page using the authorized Token
            payload = {
                "access_token": token,
                "title": title, 
                "author_name": author,
                "content": [{"tag": "pre", "children": [text]}], 
                "return_content": True
            }
            r = await client.post("https://api.telegra.ph/createPage", json=payload)
            url = r.json().get("result", {}).get("url", "")
            
            if not url:
                return "❌ Telegraph API did not return a valid URL."
            
            # 3. Modify for Indian ISP compatibility
            return url.replace("telegra.ph", "graph.org")
        except Exception as e:
            return f"❌ Telegraph API Connection Error: {e}"