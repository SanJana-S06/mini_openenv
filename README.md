---
title: Mini Productivity Openenv
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Mini Productivity OpenEnv

A sophisticated desktop productivity environment for the OpenEnv framework, enabling AI agents to simulate real-world office tasks through programmatic GUI automation. This environment bridges the gap between language models and physical desktop interactions, allowing agents to draft documents, manage workspaces, and complete productivity workflows.

## Key Features

- **Realistic GUI Simulation**: Uses PyAutoGUI and Tkinter to create an authentic desktop experience with virtual windows, text input, and submission workflows.
- **Task-Aware Reward System**: Intelligent reward calculation based on keyword matching and task completion, supporting easy, medium, and hard difficulty levels.
- **OpenAI Integration**: Seamless API integration with configurable models (GPT-4o-mini) for agent decision-making, with robust fallback mechanisms.
- **Structured Action Space**: Well-defined action types (OPEN_WORKSPACE, TYPE_TEXT, CLICK_SUBMIT, etc.) enabling precise control over productivity tasks.
- **Comprehensive Logging**: Built-in structured output logging ([START]/[STEP]/[END]) for evaluation and debugging.

## Architecture

### Core Components

- **`mini/openenv_env.py`**: Main environment class implementing the OpenEnv interface with GUI automation and reward logic.
- **`server/app.py`**: FastAPI server exposing REST endpoints for environment interaction.
- **`inference.py`**: Baseline inference script demonstrating OpenAI-powered agent behavior with timeout handling and structured logging.

### Environment Design

The environment simulates a desktop productivity application where agents must:
1. Open the workspace interface
2. Type relevant content based on the task
3. Submit the completed work

### Reward Mechanism

Rewards are calculated progressively:
- **Workspace Opening**: +0.1 for successful workspace access
- **Keyword Matching**: Up to +0.6 based on task-specific keywords found in the draft
- **Submission**: +0.3 for completing the task

Hard tasks (e.g., incident_report) require 4+ keyword matches for maximum reward.

## Tasks

- **meeting_note** (Easy): Compose meeting notes with agenda and next steps
- **customer_response** (Medium): Draft polite customer support replies
- **incident_report** (Hard): Write incident reports with root cause, impact, and resolution

## API Integration

The inference script integrates with OpenAI's API for intelligent action selection:

```python
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY, timeout=30.0)
response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[system_prompt, task_prompt, user_prompt],
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS
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
