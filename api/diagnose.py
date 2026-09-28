from http.server import BaseHTTPRequestHandler
import json, os, base64, io, re
from groq import Groq
from gtts import gTTS

SYSTEM = (
    "You have to act as a professional doctor, I know you are not, but this is for learning purposes. "
    "With what I see, I think you have .... If you make a differential, suggest some remedies for them. "
    "Do not add any numbers or special characters in your response. Your response should be in one long paragraph. "
    "Always answer as if you are talking to a real person. Do not respond as an AI model in markdown; "
    "your answer should mimic that of an actual doctor, not an AI bot. Keep your answer concise (max 2 sentences). "
    "No preamble, start your answer right away please."
)
# Change with the GROQ_MODEL environment variable if Groq retires this model again
MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")


class handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            n = int(self.headers.get("content-length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            symptoms = (data.get("symptoms") or "").strip()[:1000]
            if not symptoms:
                return self._send(400, {"error": "Please describe your symptoms to proceed."})
            key = os.environ.get("GROQ_API_KEY")
            if not key:
                return self._send(500, {"error": "Server is missing GROQ_API_KEY."})
            content = [{"type": "text", "text": SYSTEM + " " + symptoms}]
            image = data.get("image")
            if image:
                content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image}})
            client = Groq(api_key=key)
            res = client.chat.completions.create(messages=[{"role": "user", "content": content}], model=MODEL, max_completion_tokens=1024)
            text = res.choices[0].message.content or ""
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
            if not text:
                return self._send(500, {"error": "The model returned an empty answer. Please try again."})
            audio = None
            try:
                buf = io.BytesIO()
                gTTS(text=text, lang="en").write_to_fp(buf)
                audio = base64.b64encode(buf.getvalue()).decode()
            except Exception:
                pass
            self._send(200, {"text": text, "audio": audio})
        except Exception as e:
            self._send(500, {"error": "Analysis Error: " + str(e)})
