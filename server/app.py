from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from typing import Optional
from mini.openenv_env import MiniOpenEnv, MiniOpenEnvAction

app = FastAPI(title="Mini OpenEnv Server")
env = None

class ResetRequest(BaseModel):
    task_name: Optional[str] = None
    model_config = ConfigDict(extra="allow")   # ✅ Pydantic v2

class StepRequest(BaseModel):
    action: MiniOpenEnvAction
    model_config = ConfigDict(extra="allow")   # ✅ Pydantic v2

@app.get("/")
async def root():
    return {"message": "Server is running"}

@app.post("/reset")
async def reset(request: Request) -> dict:
    global env
    from mini.openenv_env import MiniOpenEnv
    try:
        body = await request.json()
        task_name = body.get("task_name", "meeting_note")
    except Exception:
        task_name = "meeting_note"
    env = MiniOpenEnv(task_name=task_name)
    observation = env.reset(task_name=task_name)
    return {
        "observation": observation.model_dump(),   # ✅ Pydantic v2
        "reward": 0.0,
        "done": False,
        "info": {"task_name": env.task_name},
    }

@app.post("/step")
def step(request: StepRequest) -> dict:
    if env is None:
        raise HTTPException(status_code=400, detail="Call /reset first")
    try:
        observation, reward, done, info = env.step(request.action)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "observation": observation.model_dump(),   # ✅ Pydantic v2
        "reward": reward,
        "done": done,
        "info": info,
    }

@app.get("/state")
def state() -> dict:
    if env is None:
        raise HTTPException(status_code=400, detail="Call /reset first")
    observation = env.state()
    return {
        "observation": observation.model_dump(),   # ✅ Pydantic v2
        "info": {"task_name": env.task_name},
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ping")
def ping() -> dict:
    return {"ok": True}

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()