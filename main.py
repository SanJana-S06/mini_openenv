import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from huggingface_hub import login
from transformers import pipeline

app = FastAPI(title="Hugging Face Text Generation API")

# Global model pipeline
generator = None

class GenerateRequest(BaseModel):
    prompt: str
    max_length: int = 50
    num_return_sequences: int = 1

def authenticate_huggingface():
    token = os.getenv("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN environment variable is not set. Please set it to your Hugging Face token.")
    login(token)

def load_model():
    global generator
    generator = pipeline("text-generation", model="gpt2")

@app.on_event("startup")
async def startup_event():
    try:
        authenticate_huggingface()
        load_model()
    except ValueError as e:
        print(f"Authentication error: {e}")
        raise

@app.post("/generate")
def generate_text(request: GenerateRequest):
    if generator is None:
        raise HTTPException(status_code=500, detail="Model not loaded. Check server startup.")
    try:
        results = generator(
            request.prompt,
            max_length=request.max_length,
            num_return_sequences=request.num_return_sequences
        )
        return {"generated_texts": [result['generated_text'] for result in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.get("/health")
def health():
    return {"status": "ok"}