PRIORITY_PROMPT_TEMPLATE = """\
You are a strictly factual, concise project management assistant. Analyze the task below \
within its project context and assign one of four priority levels: 0 (lowest), 1, 2, or 3 (highest).\n\n\
Project Title: {project_title}\n\
Project Description: {project_description}
New Task Title: "{task_title}"\n\
New Task Description: {task_description}\n\n\
Existing tasks for context (status -> title + current priority):\n\
{other_tasks}\n\n\
Respond as a strict JSON object with these exact fields and NOTHING ELSE:\n\
{"suggested_priority": 2, "reasoning": "...", "confidence": 0.85}"""


DEADLINE_PROMPT_TEMPLATE = """\
You are a project management assistant. Analyze the following task description and its project context \
to determine if there is a specific temporal cue (deadline, date, sprint window, or time reference).\n\n\
Project Title: {project_title}\n\
New Task Title: "{task_title}"\n\
New Task Description: {task_description}\n\n\
If you detect a clear deadline relative to the project timeline or explicit timeframe, calculate \
and suggest a realistic due_date (in YYYY-MM-DD format) and provide a short reason.\n\
If NO temporal reference exists or the description is purely generic, return null.\n\n\
Respond as a JSON object with these exact fields:\n\
{"suggested_due_date": "2024-12-31", "confidence": 0.75, "reasoning": "..."}"""


DESC_GEN_PROMPT_TEMPLATE = """\
You are an expert technical project manager taking brief user requests and turning them \
into structured, actionable task descriptions with clear acceptance criteria.\n\n\
Project: "{project_title}" - "{project_description}"
User's Task Title: "{task_title}"\n\n\
Expand this into a detailed task description including:\n\
1. A one-sentence Objective.\n\
2. 3 to 5 highly specific Acceptance Criteria bullets (must be verifiable).\n\
3. Relevant technical subtasks or implementation hints.\n\
Respond strictly as markdown text, NO JSON."""
