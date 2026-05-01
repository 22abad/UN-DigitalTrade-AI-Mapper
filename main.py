from dotenv import load_dotenv
load_dotenv()

from typing import Optional
import os
import json

from fastapi import FastAPI
from pydantic import BaseModel, ValidationError

import google.generativeai as genai

from utils.chunker import regex_legal_chunker

# ---------------------------------------------------------
# 1. 物理模具定义 (The Schema)
# ---------------------------------------------------------
class RDTII_Extraction(BaseModel):
    title: str
    last_update: str
    url: str
    scope: str
    provisions: str
    impact: str
    requires_human_review: bool = True

class TextRequest(BaseModel):
    text: Optional[str] = None

app = FastAPI()

# ---------------------------------------------------------
# 2. 弹药装载 (API Key Configuration)
# ---------------------------------------------------------
_GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if _GEMINI_KEY:
    genai.configure(api_key=_GEMINI_KEY)
else:
    print("🚨 致命警告：未检测到 GEMINI_API_KEY，请检查项目根目录的 .env 文件！")

# ---------------------------------------------------------
# 3. 核动力榨汁机 (Gemini Extraction Engine)
# ---------------------------------------------------------
def call_gemini_for_chunk(chunk: str) -> Optional[dict]:
    # 典狱长级别的全英文 Prompt 锁死大模型输出，防幻觉第一道防线
    prompt = f"""You are an expert UN digital trade policy analyst. Your task is to extract cross-border data provisions and map them to the RDTII 2.1 framework.

CRITICAL RULES (ABSOLUTE COMPLIANCE REQUIRED):
1. STRICT JSON SCHEMA: You MUST output a valid JSON object strictly matching this exact structure. Do NOT omit any keys:
{{
    "title": "String. If not provided in text, output 'Not Provided'.",
    "last_update": "String. If not provided, output 'Not Provided'.",
    "url": "String. If not provided, output 'Not Provided'.",
    "scope": "String. If not provided, output 'Not Provided'.",
    "provisions": "String. MUST be an exact, character-for-character quote from the input.",
    "impact": "String. Explicitly state the RDTII Pillar (e.g., Pillar 6.4) and explain the policy impact.",
    "requires_human_review": true
}}
2. NO HALLUCINATION: Do not invent missing metadata.

Input text:
{chunk}
"""

    try:
        # 使用 Gemini 1.5 最新的正确调用语法
        model = genai.GenerativeModel('gemini-3-flash-preview')
        resp = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0, # 剥夺创造力，强迫绝对理性
                response_mime_type="application/json", # 强迫物理输出 JSON
            )
        )
        return json.loads(resp.text)
    except Exception as e:
        print(f"🚨 赛博引擎报错 (Gemini API Error): {e}")
        return None

# ---------------------------------------------------------
# 4. API 路由与装配线 (The Pipeline)
# ---------------------------------------------------------
@app.post("/api/extract", response_model=RDTII_Extraction)
async def extract(req: TextRequest):
    sample_text = req.text or ""
    
    # 将文本丢进正则切肉机
    chunks = regex_legal_chunker(sample_text)

    # 防御机制：如果正则啥都没切出来，就把整段原文当成一个大肉块喂进去
    if not chunks:
        chunks = [sample_text]

    for chunk in chunks:
        parsed = call_gemini_for_chunk(chunk)
        if not parsed:
            continue
            
        # 🔥 降维物理修复：剥掉外层的塑料袋（列表）
        if isinstance(parsed, list):
            if len(parsed) > 0:
                parsed = parsed[0] # 把里面真正的字典掏出来
            else:
                continue
                
        try:
            # 尝试把 JSON 塞进模具，过安检
            obj = RDTII_Extraction.parse_obj(parsed)
            return obj
        except ValidationError as e:
            print(f"🚨 模具校验失败 (Validation Error): {e}")
            continue

    # 物理斩断退路：绝不给假数据。如果彻底没找到，如实反馈失败！
    return RDTII_Extraction(
        title="Not Provided",
        last_update="Not Provided",
        url="Not Provided",
        scope="Not Provided",
        provisions="No specific cross-border data transfer provisions found in this text.",
        impact="Extraction Failed or irrelevant text.",
        requires_human_review=True,
    )