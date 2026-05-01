import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from chunker import regex_legal_chunker

# ⚠️ 注意这里，多导入了一个 Form
from fastapi import FastAPI, Form
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize

app = FastAPI()

# 📡 Chenming 的向量雷达
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

# ==========================================
# 🧠 老李的防弹版 Gemini 核动力引擎
# ==========================================
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
        gemini_model = genai.GenerativeModel('gemini-3-flash-preview')
        
        # 🔥 核心特权指令：强行关闭所有安全拦截！
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        resp = gemini_model.generate_content(
            prompt, 
            generation_config=genai.types.GenerationConfig(temperature=0, response_mime_type="application/json"),
            safety_settings=safety_settings  # 👈 把特权指令装配给大模型
        )
        
        # 加强防弹：防止大模型偶尔抽风带上 ```json 的外壳
        clean_text = resp.text.strip().removeprefix('```json').removesuffix('```').strip()
        
        return json.loads(clean_text)
    except Exception as e:
        print(f"API Error: {e}")
        return None

# ⚠️ 核心防弹装甲：抛弃 JSON，改用 text: str = Form(...)
@app.post("/api/extract", response_model=RDTII_Extraction)
def extract_legal_text(text: str = Form(...)):
    
    # 直接把带无数回车的原始文本喂给你的切肉机
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
        title="N/A", last_update="N/A", url="N/A", scope="N/A", 
        provisions="No provisions found", impact="Failed", requires_human_review=True
    )
