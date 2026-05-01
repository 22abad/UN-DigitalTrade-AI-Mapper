import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from chunker import regex_legal_chunker
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


class TextRequest(BaseModel):
    text: str


@app.post("/embed")
def embed(req: TextRequest):
    vector = embed_model.encode([req.text])
    vector = normalize(vector)
    return {"vector": vector[0].tolist()}


@app.get("/health")
def health():
    return {"status": "ok"}


load_dotenv()
_GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if _GEMINI_KEY:
    genai.configure(api_key=_GEMINI_KEY)


class RDTII_Extraction(BaseModel):
    title: str
    last_update: str
    url: str
    scope: str
    provisions: str
    impact: str
    requires_human_review: bool = True


def call_gemini_for_chunk(chunk: str):
    prompt = f"""You are a UN digital trade policy analyst. Extract cross-border data provisions and map to RDTII 2.1.
Output MUST be valid JSON strictly matching this structure:
{{
    "title": "",
    "last_update": "",
    "url": "",
    "scope": "",
    "provisions": "",
    "impact": "",
    "requires_human_review": false
}}
CRITICAL RULE: Set "requires_human_review" to true ONLY IF the text is highly ambiguous or you are uncertain about the mapping. Otherwise, it MUST be false.
    Input text: {chunk}"""
    try:
        gemini_model = genai.GenerativeModel("gemini-3-flash-preview")

        resp = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )

        clean_text = (
            resp.text.strip().removeprefix("```json").removesuffix("```").strip()
        )

        return json.loads(clean_text)
    except Exception as e:
        print(f"API Error: {e}")
        return None


@app.post("/api/extract", response_model=RDTII_Extraction)
def extract_legal_text(text: str = Form(...)):
    chunks = regex_legal_chunker(text)

    for chunk in chunks:
        parsed = call_gemini_for_chunk(chunk)
        if parsed:
            if isinstance(parsed, list) and len(parsed) > 0:
                parsed = parsed[0]
            try:
                return RDTII_Extraction(**parsed)
            except Exception:
                continue
    return RDTII_Extraction(
        title="N/A",
        last_update="N/A",
        url="N/A",
        scope="N/A",
        provisions="No provisions found",
        impact="Failed",
        requires_human_review=True,
    )
