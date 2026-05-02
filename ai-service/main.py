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
    # 🧠 把洗脑指令直接融进 Prompt 的头部，绕过版本兼容性坑
    prompt = f"""[SYSTEM INSTRUCTION]
You are a senior UN digital trade policy analyst strictly following the RDTII 2.1 Methodology.
CRITICAL RULE: Cross-border data flows, data export security assessments, and overseas data transfers MUST ALWAYS be mapped to Pillar 6. NEVER map them to Pillar 4.

[TASK]
Extract provisions and map to RDTII 2.1.
Output MUST be valid JSON strictly matching:
{{
    "title": "",
    "last_update": "",
    "url": "",
    "scope": "",
    "provisions": "",
    "impact": "Detailed analysis. MUST explicitly state 'Pillar 6' if related to cross-border data.",
    "requires_human_review": false
}}

Input text: {chunk}"""

    try:
        # 🔙 恢复最简单、最不容易报错的模型调用方式
        gemini_model = genai.GenerativeModel('gemini-3.1-pro-preview')
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        resp = gemini_model.generate_content(
            prompt, 
            generation_config=genai.types.GenerationConfig(temperature=0, response_mime_type="application/json"),
            safety_settings=safety_settings
        )
        
        # 🛡️ 终极 JSON 提取法：不管大模型外面包了什么废话，只暴力掏出大括号里面的内容！
        text_resp = resp.text
        start = text_resp.find('{')
        end = text_resp.rfind('}') + 1
        if start != -1 and end != 0:
            clean_json = text_resp[start:end]
            return json.loads(clean_json)
        else:
            raise ValueError("No JSON payload found")
            
    except Exception as e:
        # 这里的报错只有在后台日志里能看见
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
