---
title: Mini Voice-Productivity Openenv
emoji: 🎙️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Mini Voice-Productivity OpenEnv

A voice-first desktop productivity environment for the OpenEnv framework, enabling AI agents to bridge the gap between human vocal intent and physical desktop automation. This system allows agents to navigate and control the computer system hands-free, performing complex office tasks through transcribed intent.

## 🌟 The Vision: Voice-to-Action
The core innovation of this environment is the **Voice-to-Action Mapping (VAM)**. While the current Phase 1 evaluation uses text-based prompts to satisfy automated validator constraints, the system is architected to treat these prompts as "Transcribed Intent" from a user's voice command.

## Key Features

- **Voice-to-Action Mapping (VAM)**: Architected to translate natural language vocal commands into structured GUI actions (OPEN, TYPE, CLICK).
- **Realistic GUI Simulation**: Uses PyAutoGUI and Tkinter to create an authentic desktop experience with virtual windows and text input.
- **Task-Aware Reward System**: Intelligent reward calculation based on keyword matching and task completion (+0.1 workspace, +0.6 keyword content, +0.3 submission).
- **Voice-Intent Logic**: Integrated with `gpt-4o-mini` to simulate intent parsing from user voice commands (e.g., *"Hey Agent, draft the meeting notes"*).
- **Comprehensive Logging**: Built-in structured output logging ([START]/[STEP]/[END]) compliant with OpenEnv evaluation requirements.

## Architecture

### Core Components

- **`mini/openenv_env.py`**: The "Muscle" - Main environment implementing GUI automation and keyword-based reward logic.
- **`server/app.py`**: The "Interface" - FastAPI server exposing REST endpoints for environment interaction.
- **`inference.py`**: The "Brain" - Optimized script demonstrating voice-intent processing with 12-second timeouts and robust fallback.

### Environment Design

The environment simulates a hands-free workstation where vocal intent triggers a three-stage workflow:
1. **Intention**: Open the workspace interface.
2. **Execution**: Type relevant content based on vocal instructions.
3. **Completion**: Submit the finalized work.

### Reward Mechanism

Rewards are calculated progressively to ensure technical validation:
- **Workspace Opening**: +0.1 for successful workspace access.
- **Keyword Matching**: Up to +0.6 based on task-specific keywords found in the draft.
- **Submission**: +0.3 for completing the task.

## Tasks

- **meeting_note** (Easy): Compose meeting notes based on voice prompts with agenda and next steps.
- **customer_response** (Medium): Draft professional customer support replies via vocal instruction.
- **incident_report** (Hard): Write complex reports requiring 4+ keyword matches for maximum reward.

## API Integration

The inference script uses provided proxy infrastructure to satisfy the **LLM Criteria Check**:

```python
# Compliant with Pre-Submission Checklist
client = OpenAI(
    base_url=os.getenv("API_BASE_URL", "[https://router.huggingface.co/v1](https://router.huggingface.co/v1)"),
    api_key=os.getenv("HF_TOKEN"), # No default for security compliance
    timeout=12.0
)
```
## Installation
```bash
pip install -r requirements.txt
```

## Running

### Local Environment
```python
from mini.openenv_env import MiniOpenEnv, MiniOpenEnvAction

env = MiniOpenEnv(task_name="meeting_note")
obs = env.reset()
action = MiniOpenEnvAction(type="OPEN_WORKSPACE")
obs, reward, done, info = env.step(action)
```

### Server
```bash
python -m server.app
```

### Inference
```bash
export HF_TOKEN="your-token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="gpt-4o-mini"
python inference.py
```

## Validation

Run the pre-submission validator:

```bash
chmod +x validate-submission.sh
./validate-submission.sh https://your-space.hf.space
```

## Docker

Build and run:

```bash
docker build -t mini-openenv .
docker run -p 7860:7860 mini-openenv
```

## Technical Highlights

- **Timeout Protection**: 30-second API timeouts prevent evaluation hangs
- **Fallback Logic**: Robust error handling with deterministic fallbacks
- **Virtual Display**: Xvfb integration for headless GUI operations
- **Structured Output**: Compliant with OpenEnv evaluation requirements
- **Scalable Design**: Easy extension for additional productivity tasks
- **Voice-First Scaling**: Architected for easy extension into real-time Speech-to-Text (STT) integration.
