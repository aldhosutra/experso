"""Local models through Ollama's HTTP API (no agent harness, no cloud).
Uses Ollama's native structured output (format=<JSON Schema>) and sends the
images inline, so pick a vision model (e.g. gemma3, qwen2.5vl, llama3.2-vision)."""
import base64
import json
import os
import urllib.request

from .base import Extractor
from .schema import RESULT_SCHEMA, SYSTEM_PROMPT, build_prompt, parse_json


class OllamaExtractor(Extractor):
    name = "ollama"

    def run_json(self, prompt: str, schema: dict, system: str = "",
                 images: list[str] | None = None, image_label: str = "image") -> dict:
        if not self.model:
            raise SystemExit("--extractor ollama needs --model (a vision model, e.g. gemma3:12b)")
        images = images or []
        refs = [f"{image_label} {i}" for i in range(1, len(images) + 1)]
        prompt = (prompt.replace("{images}", "\n".join(refs) or "(none)")
                  .replace("{image_how}", "they are attached to this message in order"))
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt,
             "images": [base64.b64encode(open(p, "rb").read()).decode() for p in images]}]
        body = {"model": self.model, "stream": False, "format": schema, "messages": messages,
                "options": {"num_ctx": self.options.get("num_ctx", 32768), "temperature": 0}}
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        if not host.startswith("http"):
            host = "http://" + host
        req = urllib.request.Request(f"{host}/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.options.get("timeout", 1200)) as r:
            reply = json.load(r)["message"]["content"]
        return parse_json(reply, schema)

    def extract(self, post, creator: str) -> dict:
        prompt = build_prompt(post, creator, image_refs=["{images}"], image_how="{image_how}")
        return self.run_json(prompt, RESULT_SCHEMA, SYSTEM_PROMPT, post.images, "slide")
