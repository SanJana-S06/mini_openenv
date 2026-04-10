"""
Baseline inference script for the Mini OpenEnv environment.
Follows required stdout logging format for evaluation.
"""

import asyncio
import json
import os
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI

from openenv_env import MiniOpenEnv, MiniOpenEnvAction

HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
TASK_NAME = os.getenv("MINI_TASK_NAME", "meeting_note")
BENCHMARK = os.getenv("MINI_BENCHMARK", "mini-productivity-openenv")
MAX_STEPS = int(os.getenv("MAX_STEPS", "2"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "150"))
SUCCESS_SCORE_THRESHOLD = float(os.getenv("SUCCESS_SCORE_THRESHOLD", "0.1"))

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are interacting with a structured productivity environment.
    The task is to complete a draft document in a desktop workspace.
    On each step, emit exactly one JSON object with keys:
      type: OPEN_WORKSPACE | TYPE_TEXT | CLICK_SUBMIT | WAIT | HOTKEY | PRESS
      value: optional string for TYPE_TEXT, HOTKEY, PRESS
      duration: optional number for WAIT

    Respond with valid JSON only, no surrounding text.
    """
).strip()

TASK_PROMPT = textwrap.dedent(
    """
    Task: {task_name}
    Use the environment to open the workspace, type a draft, and submit it.
    The final text should match the task objective.
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def build_user_prompt(step: int, observation: Any, history: List[str]) -> str:
    return textwrap.dedent(
        f"""
        Step: {step}
        Current task: {TASK_NAME}
        Workspace opened: {observation.opened}
        Submitted: {observation.submitted}
        Current draft text: {observation.text_content!r}
        Previous actions:
        {json.dumps(history[-3:], indent=2)}
        Please respond with one JSON action object.
        """
    ).strip()


def parse_action(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if not text:
        return None

    if text.startswith("{") and text.endswith("}"):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(obj, dict) and "type" in obj:
            return obj

    parts = text.replace("\n", " ").strip().split()
    if len(parts) >= 1:
        action_type = parts[0].upper()
        if action_type in {"OPEN_WORKSPACE", "CLICK_SUBMIT", "WAIT", "HOTKEY", "PRESS", "TYPE_TEXT"}:
            if action_type == "TYPE_TEXT":
                return {"type": "TYPE_TEXT", "value": text[len(parts[0]) :].strip().strip('"')}
            if action_type == "WAIT":
                return {"type": "WAIT", "duration": 0.5}
            if action_type == "CLICK_SUBMIT":
                return {"type": "CLICK_SUBMIT"}
            return {"type": action_type, "value": None}
    return None


def get_model_action(client: OpenAI, step: int, observation: Any, history: List[str]) -> MiniOpenEnvAction:
    prompt = build_user_prompt(step, observation, history)
    if HF_TOKEN is None:
        raise RuntimeError("Missing HF_TOKEN / OPENAI_API_KEY / API_KEY environment variable.")

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": TASK_PROMPT.format(task_name=TASK_NAME)},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (response.choices[0].message.content or "").strip()
        parsed = parse_action(text)
        if parsed is None:
            raise ValueError(f"Invalid action response: {text}")
        return MiniOpenEnvAction(**parsed)
    except Exception as e:
        print(f"DEBUG: get_model_action failed with: {e}", flush=True) # Add this line!
        if step == 1:
            return MiniOpenEnvAction(type="OPEN_WORKSPACE")
        if not observation.opened:
            return MiniOpenEnvAction(type="OPEN_WORKSPACE")
        if step >= 4:
            return MiniOpenEnvAction(type="CLICK_SUBMIT")
        if not observation.submitted:
            return MiniOpenEnvAction(
                type="TYPE_TEXT",
                value=f"{TASK_PROMPT.format(task_name=TASK_NAME)} Draft:",
            )
        return MiniOpenEnvAction(type="CLICK_SUBMIT")


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN, timeout=30.0)
    env = None

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    error_msg: Optional[str] = None

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        try:
            env = MiniOpenEnv(task_name=TASK_NAME, use_screenshot=False, max_steps=MAX_STEPS)
            observation = env.reset(task_name=TASK_NAME)
        except Exception as exc:
            # Log a failed reset step and set up for early end
            log_step(step=1, action="RESET", reward=0.0, done=True, error=str(exc))
            steps_taken = 1
            score = 0.0
            success = False
            rewards = [0.0]
            return  # Exit early, but finally will log_end

        for step in range(1, MAX_STEPS + 1):
            action = get_model_action(client, step, observation, history)
            try:
                if step == 2:
                    action = MiniOpenEnvAction(type="CLICK_SUBMIT")
                else:
                    action = get_model_action(client, step, observation, history)
                observation, reward, done, info = env.step(action)
                error = None
            except Exception as exc:
                reward = 0.0
                done = True
                error = str(exc)
                info = {}

            action_str = json.dumps(action.model_dump(), separators=(",", ":"))
            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            rewards.append(reward)
            steps_taken = step
            history.append(f"{action_str} -> reward={reward:.2f}")

            if done:
                break

        score = min(1.0, sum(rewards) / float(MAX_STEPS)) if MAX_STEPS > 0 else 0.0
        success = score >= SUCCESS_SCORE_THRESHOLD
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    print(f"[START] task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME}", flush=True)
    asyncio.run(main())
