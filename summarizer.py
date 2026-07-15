import os
import re
import json
import requests

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from config import (
    QWEN_MODEL,
    LLAMA_N_CTX,
    LLAMA_N_THREADS,
    MAX_TOKENS_SUMMARY,
    MAX_TOKENS_MOM,
    USE_OLLAMA,
    OLLAMA_URL,
    OLLAMA_MODEL,
)


class QwenSummarizer:

    def __init__(self):
        self._llm = None
        self._use_ollama = bool(USE_OLLAMA)

        if self._use_ollama:
            print(f"[Summarizer] Configured to use Ollama at {OLLAMA_URL}, model '{OLLAMA_MODEL}'.")
        else:
            if os.path.isfile(QWEN_MODEL):
                if Llama is None:
                    print(
                        "[Summarizer] ERROR: 'llama-cpp-python' is not installed, but local model path is set. Please install it or use Ollama."
                    )
                else:
                    print("[Summarizer] Loading Qwen2.5 model ...")
                    self._llm = Llama(
                        model_path=QWEN_MODEL,
                        n_ctx=LLAMA_N_CTX,
                        n_threads=LLAMA_N_THREADS,
                        verbose=False,
                    )
                    print("[Summarizer] Model loaded.")
            else:
                print(
                    f"[Summarizer] Qwen model not found at {QWEN_MODEL}; using fallback summaries."
                )

    def _fallback_summary(self, combined_text: str, max_items: int, heading: str) -> str:
        text = combined_text.strip()
        if not text:
            return f"{heading}\n- No transcript available yet."

        lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
        if not lines:
            lines = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]

        bullets = []
        for line in lines[:max_items]:
            bullets.append(f"- {line[:240]}")

        return f"{heading}\n" + "\n".join(bullets)

    def _chat(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        # Ollama path: post a combined prompt to the Ollama HTTP API
        if self._use_ollama:
            prompt = f"System:\n{system_prompt}\n\nUser:\n{user_prompt}"
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "stream": False,
            }
            try:
                resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=25)
                resp.raise_for_status()
                data = resp.json()

                # Try several common response shapes to extract text defensively.
                text = None
                if isinstance(data, dict):
                    if "response" in data and isinstance(data["response"], str):
                        text = data["response"]
                    elif "text" in data and isinstance(data["text"], str):
                        text = data["text"]
                    elif "output" in data and isinstance(data["output"], str):
                        text = data["output"]
                    elif "choices" in data and isinstance(data["choices"], list) and data["choices"]:
                        first = data["choices"][0]
                        if isinstance(first, dict):
                            if "text" in first and isinstance(first["text"], str):
                                text = first["text"]
                            elif "message" in first and isinstance(first["message"], dict):
                                msg = first["message"]
                                if "content" in msg:
                                    content = msg["content"]
                                    if isinstance(content, str):
                                        text = content
                                    elif isinstance(content, dict) and "text" in content:
                                        text = content["text"]
                if not text:
                    # Last resort: raw response body
                    text = resp.text
                return text.strip()
            except Exception as e:
                print(f"[Summarizer] Ollama error: {e}")
                return self._fallback_summary(user_prompt, 5, "Fallback summary")

        # llama-cpp-python path (existing behavior)
        if self._llm is None:
            return self._fallback_summary(user_prompt, 5, "Fallback summary")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
        response = self._llm.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3,
            top_p=0.9,
        )
        return response["choices"][0]["message"]["content"].strip()

    def intermediate_summary(self, combined_transcript: str) -> str:
        system = (
            "You are a meeting assistant. Summarize the transcript below "
            "into concise bullet points covering key points, decisions, and action items."
        )
        user = f"Transcript so far:\n\n{combined_transcript}"
        return self._chat(system, user, MAX_TOKENS_SUMMARY)

    def final_mom(self, combined_transcript: str, intermediate_summaries: list[str], title: str = "Meeting", meeting_id: int = None, date_time: str = None) -> str:
        def get_structured_fallback():
            text = combined_transcript.strip()
            bullets = []
            if text:
                # Clean up prompt prefix if user_prompt was passed
                clean_text = re.sub(r'^(Full Transcript:|Intermediate Summaries:)', '', text).strip()
                lines = [line.strip() for line in re.split(r"[\r\n]+", clean_text) if line.strip()]
                if not lines:
                    lines = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", clean_text) if sentence.strip()]
                for line in lines[:8]:
                    bullets.append(f"- {line[:240]}")
            else:
                bullets.append("- No transcript available yet.")
            
            bullet_str = "\n".join(bullets)
            meeting_id_str = f"#{meeting_id}" if meeting_id else "N/A"
            
            return f"""### 1. Meeting Metadata
- **Meeting Title:** {title}
- **Date & Time:** {date_time or 'N/A'}
- **Meeting ID:** {meeting_id_str}

### 2. Key Discussion Points
{bullet_str}

### 3. Major Decisions Made
- *No AI model was active to extract decisions. Please refer to the transcript above.*

### 4. Action Items
- [ ] Review raw transcript for action items.
"""

        if self._llm is None and not self._use_ollama:
            return get_structured_fallback()

        summaries_text = "\n\n---\n\n".join(intermediate_summaries) if intermediate_summaries else "None"
        meeting_id_str = f"#{meeting_id}" if meeting_id else "N/A"
        
        system = (
            "You are a professional meeting secretary.\n"
            "Generate a formal, highly structured Minutes of Meeting (MoM) document with the following sections:\n\n"
            "### 1. Meeting Metadata\n"
            "Include the following details in a list:\n"
            f"- **Meeting Title:** {title}\n"
            f"- **Date & Time:** {date_time or 'N/A'}\n"
            f"- **Meeting ID:** {meeting_id_str}\n\n"
            "### 2. Key Discussion Points\n"
            "Summarize the key points discussed, including participants' opinions or stances and general flow of discussion.\n\n"
            "### 3. Major Decisions Made\n"
            "List any key decisions or agreements reached during the meeting.\n\n"
            "### 4. Action Items\n"
            "A clear, actionable list of tasks. Format each task as a markdown checkbox: '- [ ] task description'. If an assignee is mentioned or implied, include it as '- [ ] task description (Assignee: Name)'."
        )
        user = (
            f"Full Transcript:\n\n{combined_transcript}\n\n"
            f"Intermediate Summaries:\n\n{summaries_text}"
        )
        
        try:
            res = self._chat(system, user, MAX_TOKENS_MOM)
            if res.startswith("Fallback summary"):
                return get_structured_fallback()
            return res
        except Exception:
            return get_structured_fallback()