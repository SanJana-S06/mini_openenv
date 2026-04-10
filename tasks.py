[
  {
    "task_id": "task_0",
    "task_name": "open_workspace",
    "difficulty": "easy",
    "description": "Initialize the environment and open the primary workspace interface.",
    "goal": "The 'opened' state should be true.",
    "max_steps": 5
  },
  {
    "task_id": "task_1",
    "task_name": "draft_meeting_note",
    "difficulty": "medium",
    "description": "Type a meeting agenda containing key business terms.",
    "goal": "The text_content must include 'meeting', 'agenda', and 'action items'.",
    "max_steps": 10
  },
  {
    "task_id": "task_2",
    "task_name": "complete_and_submit",
    "difficulty": "hard",
    "description": "Draft a full note and trigger the system submission/save process.",
    "goal": "Both 'submitted' and 'verified_goal' must be true with a 1.0 reward.",
    "max_steps": 15
  }
]