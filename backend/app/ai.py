import base64, json, os
import httpx
from .schemas import AnalysisResult

class AIUnavailable(RuntimeError): pass

async def analyze_image(image_bytes: bytes, mime_type: str) -> AnalysisResult:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise AIUnavailable("Image analysis is not configured. Add OPENAI_API_KEY and a vision-capable VISION_MODEL to backend/.env, then restart the API.")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("VISION_MODEL", "gpt-4o-mini")
    prompt = '''Analyze the actual food image. Return ONLY JSON matching this schema: {"items":[{"food_name":"string","portion_g":100,"ingredients_observed":[],"ingredients_likely":[],"calories":100,"protein_g":3,"carbs_g":20,"fat_g":2,"fibre_g":3,"confidence":0.5,"calorie_range":[80,130],"data_source":"AI visual estimate; not a verified food database","assumptions":[]}],"questions":[],"overall_notes":[]}. Separate visible components in mixed meals. Do not claim hidden ingredients or exact weight from pixels. Give realistic ranges and confidence. If food is unclear, say so and ask a question rather than guessing. Values are provisional estimates, not clinical advice.'''
    body = {"model": model, "temperature": 0, "response_format": {"type":"json_object"}, "messages":[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"}}]}]}
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(f"{base_url}/chat/completions", headers={"Authorization":f"Bearer {api_key}"}, json=body)
        r.raise_for_status()
        payload = r.json()
        content = payload["choices"][0]["message"]["content"]
        return AnalysisResult.model_validate(json.loads(content))
    except httpx.HTTPStatusError as e:
        raise AIUnavailable(f"Vision provider returned HTTP {e.response.status_code}. Check the key, model access and provider quota.") from e
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as e:
        raise AIUnavailable(f"Could not obtain a valid structured vision response: {type(e).__name__}. No analysis was saved.") from e
