from __future__ import annotations
import base64
import io
import json
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import psutil
from pydantic import BaseModel, Field

try:
    import tkinter as tk
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from openenv import Environment
except ImportError:  # pragma: no cover
    class Environment:  # type: ignore
        pass

_PYAUTOGUI = None


def _get_pyautogui():
    global _PYAUTOGUI
    if _PYAUTOGUI is None:
        import pyautogui as _pyautogui

        _pyautogui.PAUSE = 0.5
        _pyautogui.FAILSAFE = False
        _PYAUTOGUI = _pyautogui
    return _PYAUTOGUI


class MiniOpenEnvAction(BaseModel):
    type: Literal["OPEN_WORKSPACE", "TYPE_TEXT", "CLICK_SUBMIT", "WAIT", "HOTKEY", "PRESS"]
    value: Optional[str] = None
    duration: float = 0.5


class MiniOpenEnvObservation(BaseModel):
    window_titles: List[str]
    timestamp: float
    task_name: str
    opened: bool
    submitted: bool
    text_content: str
    screenshot_png: Optional[str] = None


class MiniOpenEnvReward(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0)
    detail: str


@dataclass
class ActionResult:
    success: bool
    message: str
    details: Dict[str, Any]


@dataclass
class TaskDefinition:
    name: str
    description: str
    keywords: List[str]
    min_matches: int
    difficulty: str


TASK_DEFINITIONS: Dict[str, TaskDefinition] = {
    "meeting_note": TaskDefinition(
        name="meeting_note",
        description="Compose a short meeting note with agenda and next steps.",
        keywords=["meeting", "agenda", "next steps", "timeline", "action items"],
        min_matches=3,
        difficulty="easy",
    ),
    "customer_response": TaskDefinition(
        name="customer_response",
        description="Draft a polite customer support reply that thanks the customer and summarizes the issue.",
        keywords=["customer", "thank you", "support", "issue", "help"],
        min_matches=3,
        difficulty="medium",
    ),
    "incident_report": TaskDefinition(
        name="incident_report",
        description="Write a brief incident report that includes root cause, impact, and resolution.",
        keywords=["incident", "root cause", "impact", "resolution", "next steps"],
        min_matches=4,
        difficulty="hard",
    ),
}

TASKS_FILE = Path(__file__).resolve().parents[1] / "tasks.json"


def _load_tasks_file(path: Path = TASKS_FILE) -> List[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            tasks = json.load(f)
        if not isinstance(tasks, list):
            raise ValueError("tasks.json must contain a list of tasks.")
        return tasks
    except FileNotFoundError:
        return []
    except Exception:
        return []


TASKS = _load_tasks_file()


class TaskWorkspace:
    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.window: Optional[Any] = None
        self.text_widget: Optional[Any] = None
        self.submitted = False
        self.text_content = ""
        self._lock = threading.Lock()

    def start(self) -> None:
        if self.running:
            return

        if TK_AVAILABLE:
            self.thread = threading.Thread(target=self._run_tk, daemon=True)
            self.thread.start()
            timeout = time.time() + 5
            while not self.running and time.time() < timeout:
                time.sleep(0.05)
        else:
            self.running = True

    def _run_tk(self) -> None:
        try:
            root = tk.Tk()
            root.title("Mini Task Workspace")
            root.geometry("720x520+100+100")
            self.window = root
            self.text_widget = tk.Text(root, width=90, height=20)
            self.text_widget.pack(padx=10, pady=10)

            def submit() -> None:
                with self._lock:
                    self.text_content = self.text_widget.get("1.0", "end").strip()
                    self.submitted = True

            button = tk.Button(root, text="Submit", command=submit)
            button.pack(pady=8)
            self.running = True
            root.protocol("WM_DELETE_WINDOW", root.quit)
            root.mainloop()
        except Exception:
            self.running = True

    def stop(self) -> None:
        self.running = False
        if TK_AVAILABLE and self.window is not None:
            try:
                self.window.quit()
                self.window.destroy()
            except Exception:
                pass

    def append_text(self, text: str) -> None:
        with self._lock:
            self.text_content += text

    def submit(self) -> None:
        with self._lock:
            self.submitted = True

    def get_text(self) -> str:
        with self._lock:
            return self.text_content.strip()

    def is_submitted(self) -> bool:
        with self._lock:
            return self.submitted


class MiniOpenEnv(Environment):
    """Typed OpenEnv environment for desktop task drafting with PyAutoGUI actions."""

    def __init__(self, task_name: str = "meeting_note", use_screenshot: bool = False, max_steps: int = 10) -> None:
        self.task_name = task_name
        self.use_screenshot = use_screenshot
        self.max_steps = max_steps
        self.step_count = 0
        self.done = False
        self.last_action: Optional[MiniOpenEnvAction] = None
        self.current_observation: MiniOpenEnvObservation = self._default_observation()
        self.current_reward: MiniOpenEnvReward = MiniOpenEnvReward(value=0.0, detail="reset")
        self.workspace = TaskWorkspace()
        time.sleep(2)  # Give Xvfb time to start
        self.tasks = TASKS
        self.current_task: Optional[Dict[str, Any]] = None
        self.task_def = TASK_DEFINITIONS.get(self.task_name, TASK_DEFINITIONS["meeting_note"])
        if self.tasks:
            default_task = self._find_task(self.task_name) or self.tasks[0]
            self._apply_task(default_task)
        self.reset(task_name=self.task_name)

    def _find_task(self, task_name: str) -> Optional[Dict[str, Any]]:
        for task in self.tasks:
            if task.get("task_name") == task_name:
                return task
        return None

    def _apply_task(self, task: Dict[str, Any]) -> None:
        self.current_task = task
        self.task_name = task.get("task_name", self.task_name)
        self.max_steps = int(task.get("max_steps", self.max_steps))
        self.task_def = TASK_DEFINITIONS.get(self.task_name, TASK_DEFINITIONS["meeting_note"])

    def _default_observation(self) -> MiniOpenEnvObservation:
        return MiniOpenEnvObservation(
            window_titles=[],
            timestamp=time.time(),
            task_name=self.task_name,
            opened=False,
            submitted=False,
            text_content="",
            screenshot_png=None,
        )

    def reset(self, task_name: Optional[str] = None) -> MiniOpenEnvObservation:
        if task_name is not None:
            task = self._find_task(task_name)
            if task is not None:
                self._apply_task(task)
            else:
                self.task_name = task_name
                self.task_def = TASK_DEFINITIONS.get(self.task_name, TASK_DEFINITIONS["meeting_note"])
        elif self.current_task is not None:
            self._apply_task(self.current_task)

        self.step_count = 0
        self.done = False
        self.last_action = None

        try:
            self.workspace.stop()
        except Exception:
            pass

        self.workspace = TaskWorkspace()
        try:
            self.workspace.start()
        except Exception:
            self.workspace.running = True

        try:
            self.current_observation = self._capture_observation()
        except Exception as exc:
            self.current_observation = self._default_observation()
            self.current_reward = MiniOpenEnvReward(value=0.0, detail=f"reset_exception: {exc}")
            return self.current_observation

        self.current_reward = MiniOpenEnvReward(value=0.0, detail="reset")
        return self.current_observation

    def step(self, action: MiniOpenEnvAction) -> Tuple[MiniOpenEnvObservation, float, bool, Dict[str, Any]]:
        if self.done:
            raise RuntimeError("Episode already finished. Call reset() before step().")

        self.step_count += 1
        self.last_action = action

        result = self._execute_action(action)
        self.current_observation = self._capture_observation()
        self.current_reward = self._compute_reward(self.current_observation, result)
        self.done = self._compute_done(self.current_observation)

        if self.step_count >= self.max_steps:
            self.done = True

        info: Dict[str, Any] = {
            "task_name": self.task_name,
            "step_count": self.step_count,
            "action": action.dict(),
            "result": result.__dict__,
            "progress": self._task_progress(self.current_observation),
            "missing_keywords": self._missing_keywords(self.current_observation),
            "verified_goal": self._verify_goal(self.current_observation),
        }

        return self.current_observation, float(self.current_reward.value), self.done, info

    def state(self) -> MiniOpenEnvObservation:
        return self.current_observation

    def close(self) -> None:
        self.workspace.stop()

    def _execute_action(self, action: MiniOpenEnvAction) -> ActionResult:
        if action.type == "OPEN_WORKSPACE":
            self.workspace.start()
            return ActionResult(True, "Workspace opened", {})

        if action.type == "TYPE_TEXT":
            if not action.value:
                return ActionResult(False, "TYPE_TEXT requires a value", {})
            self._focus_workspace()
            try:
                pyautogui = _get_pyautogui()
                pyautogui.typewrite(action.value, interval=0.05)
            except Exception:
                pass
            self.workspace.append_text(action.value)
            return ActionResult(True, "Text typed", {"length": len(action.value)})

        if action.type == "CLICK_SUBMIT":
            self._focus_workspace()
            try:
                pyautogui = _get_pyautogui()
                pyautogui.click(120, 500)
            except Exception:
                pass
            self.workspace.submit()
            return ActionResult(True, "Submit clicked", {})

        if action.type == "WAIT":
            time.sleep(max(0.0, action.duration))
            return ActionResult(True, "Waited", {"duration": action.duration})

        if action.type == "HOTKEY":
            if action.value:
                keys = [key.strip() for key in action.value.split("+") if key.strip()]
                try:
                    pyautogui = _get_pyautogui()
                    pyautogui.hotkey(*keys)
                except Exception:
                    pass
                return ActionResult(True, "Hotkey pressed", {"keys": keys})
            return ActionResult(False, "HOTKEY requires a value", {})

        if action.type == "PRESS":
            if action.value:
                try:
                    pyautogui = _get_pyautogui()
                    pyautogui.press(action.value)
                except Exception:
                    pass
                return ActionResult(True, "Key pressed", {"key": action.value})
            return ActionResult(False, "PRESS requires a value", {})

        return ActionResult(False, f"Unsupported action type: {action.type}", {})

    def _focus_workspace(self) -> None:
        try:
            pyautogui = _get_pyautogui()
            pyautogui.click(150, 150)
        except Exception:
            pass

    def _capture_observation(self) -> MiniOpenEnvObservation:
        try:
            return MiniOpenEnvObservation(
                window_titles=self._list_window_titles(),
                timestamp=time.time(),
                task_name=self.task_name,
                opened=self.workspace.running,
                submitted=self.workspace.is_submitted(),
                text_content=self.workspace.get_text(),
                screenshot_png=self._capture_screenshot_png() if self.use_screenshot else None,
            )
        except Exception:
            return MiniOpenEnvObservation(
                window_titles=[],
                timestamp=time.time(),
                task_name=self.task_name,
                opened=getattr(self.workspace, "running", False),
                submitted=getattr(self.workspace, "submitted", False),
                text_content="",
                screenshot_png=None,
            )

    def _capture_screenshot_png(self) -> Optional[str]:
        try:
            pyautogui = _get_pyautogui()
            image = pyautogui.screenshot()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception:
            # Return a blank black image instead of None
            if PIL_AVAILABLE:
                try:
                    img = Image.new('RGB', (100, 100), color='black')
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    return base64.b64encode(buffer.getvalue()).decode("utf-8")
                except Exception:
                    pass
            return None

    def _list_window_titles(self) -> List[str]:
        titles: List[str] = []
        try:
            pyautogui = _get_pyautogui()
            windows = pyautogui.getAllWindows()
            for window in windows:
                if window.title:
                    titles.append(window.title)
        except Exception:
            pass

        if not titles:
            titles = [proc.info.get("name", "") for proc in psutil.process_iter(["name"]) if proc.info.get("name")]
        return titles

    def _task_progress(self, observation: MiniOpenEnvObservation) -> float:
        matched = self._matched_keywords(observation)
        base_progress = 0.1 if observation.opened else 0.0
        keyword_progress = min(len(matched) / max(1, self.task_def.min_matches), 1.0) * 0.6
        submit_progress = 0.3 if observation.submitted else 0.0
        return min(1.0, base_progress + keyword_progress + submit_progress)

    def _missing_keywords(self, observation: MiniOpenEnvObservation) -> List[str]:
        matched = self._matched_keywords(observation)
        return [kw for kw in self.task_def.keywords if kw.lower() not in matched]

    def _matched_keywords(self, observation: MiniOpenEnvObservation) -> List[str]:
        text = observation.text_content.lower()
        matches: List[str] = []
        for keyword in self.task_def.keywords:
            if keyword.lower() in text:
                matches.append(keyword.lower())
        return matches

    def _compute_reward(self, observation: MiniOpenEnvObservation, result: ActionResult) -> MiniOpenEnvReward:
        if not observation.opened and self.last_action and self.last_action.type != "OPEN_WORKSPACE":
            return MiniOpenEnvReward(value=0.0, detail="workspace not opened")

        progress = self._task_progress(observation)
        reward_value = max(0.0, min(1.0, progress))
        if result.success is False:
            reward_value = max(0.0, reward_value - 0.1)
        return MiniOpenEnvReward(value=reward_value, detail=result.message)

    def _compute_done(self, observation: MiniOpenEnvObservation) -> bool:
        return observation.submitted or self.step_count >= self.max_steps

    def _verify_goal(self, observation: MiniOpenEnvObservation) -> bool:
        return observation.submitted and len(self._matched_keywords(observation)) >= self.task_def.min_matches


def get_task_names() -> List[str]:
    return [task.get("task_name") for task in TASKS if isinstance(task, dict) and task.get("task_name")]

