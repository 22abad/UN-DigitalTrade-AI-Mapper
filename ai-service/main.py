from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize

app = FastAPI()
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


class TextRequest(BaseModel):
    text: str


@app.post("/embed")
def embed(req: TextRequest):
    vector = model.encode([req.text])
    vector = normalize(vector)
    return {"vector": vector[0].tolist()}


@app.get("/health")
def health():
    return {"status": "ok"}
