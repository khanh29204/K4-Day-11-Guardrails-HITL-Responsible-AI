import asyncio
import json
import urllib.request
from google.genai import types

from core.config import LLM_PROVIDER, OLLAMA_HOST, OLLAMA_MODEL


async def chat_with_ollama(
    system_instruction: str,
    user_message: str,
    model: str = OLLAMA_MODEL,
    host: str = OLLAMA_HOST,
) -> str:
    """Send a chat request directly to local Ollama API."""
    url = f"{host}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ],
        "options": {"num_predict": 300, "temperature": 0.2},
        "stream": False,
    }

    def _call():
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "")

    try:
        return await asyncio.to_thread(_call)
    except Exception as e:
        return f"Ollama connection error: {e}"


async def chat_with_agent(agent, runner, user_message: str, session_id=None):
    """Send a message to the agent and get the response.

    Supports both Google ADK (Gemini) and Ollama local model via LLM_PROVIDER config,
    executing input & output guardrail plugins attached to agent or runner.
    """
    from types import SimpleNamespace
    user_content = types.Content(role="user", parts=[types.Part.from_text(text=user_message)])

    # Collect registered plugins from agent and runner
    plugins = []
    if agent and hasattr(agent, "plugins") and agent.plugins:
        plugins.extend(agent.plugins)
    if runner and hasattr(runner, "plugins") and runner.plugins:
        plugins.extend(runner.plugins)
    if runner and hasattr(runner, "agent") and hasattr(runner.agent, "plugins") and runner.agent.plugins:
        plugins.extend(runner.agent.plugins)

    unique_plugins = []
    for p in plugins:
        if p not in unique_plugins:
            unique_plugins.append(p)

    # 1. Input Guardrails Callback
    for plugin in unique_plugins:
        if hasattr(plugin, "on_user_message_callback"):
            decision = await plugin.on_user_message_callback(
                invocation_context=SimpleNamespace(user_id="student"),
                user_message=user_content,
            )
            if decision is not None and hasattr(decision, "parts") and decision.parts:
                blocked_text = "".join(p.text for p in decision.parts if getattr(p, "text", None))
                return blocked_text, None

    # 2. Model Generation (Ollama or Gemini ADK)
    if LLM_PROVIDER == "ollama":
        instruction = getattr(agent, "instruction", "") or ""
        response_text = await chat_with_ollama(instruction, user_message)
        session = None
    else:
        user_id = "student"
        app_name = runner.app_name if runner else "app"

        session = None
        if session_id is not None and runner:
            try:
                session = await runner.session_service.get_session(
                    app_name=app_name, user_id=user_id, session_id=session_id
                )
            except (ValueError, KeyError):
                pass

        if session is None and runner:
            try:
                session = await runner.session_service.create_session(
                    app_name=app_name, user_id=user_id
                )
            except Exception:
                session = await runner.session_service.create_session(
                    app_name=app_name, user_id=user_id
                )

        max_retries = 3
        response_text = ""
        for attempt in range(max_retries):
            try:
                final_response = ""
                sess_id = session.id if session else "default"
                async for event in runner.run_async(
                    user_id=user_id, session_id=sess_id, new_message=user_content
                ):
                    if hasattr(event, "content") and event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                final_response += part.text
                response_text = final_response
                break
            except Exception as e:
                if attempt < max_retries - 1 and ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)):
                    print(f"[chat_with_agent] Rate limit 429 hit, retrying in {(attempt + 1) * 2}s...")
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    response_text = f"Response unavailable due to API rate limit: {e}"
                    break

    # 3. Output Guardrails Callback
    for plugin in unique_plugins:
        if hasattr(plugin, "after_model_callback"):
            fake_resp = SimpleNamespace(
                content=types.Content(role="model", parts=[types.Part.from_text(text=response_text)])
            )
            mod_resp = await plugin.after_model_callback(
                callback_context=None, llm_response=fake_resp
            )
            if mod_resp and hasattr(mod_resp, "content") and mod_resp.content and mod_resp.content.parts:
                response_text = "".join(p.text for p in mod_resp.content.parts if getattr(p, "text", None))

    return response_text, session
