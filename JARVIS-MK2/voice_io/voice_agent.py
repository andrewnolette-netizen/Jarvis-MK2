# --------------------------------------------------------------
# voice_io/voice_agent.py
# Wake‑word (Porcupine) → STT (Vosk) → TTS (Coqui) → JSON‑RPC to core
# --------------------------------------------------------------
import asyncio
import json
import os
import struct
import sys
import threading
import time
from typing import Callable

import numpy as np
import pvporcupine          # pip install pvporcupine
import vosk                 # pip install vosk
import sounddevice as sd    # pip install sounddevice
from TTS.api import TTS     # pip install TTS

import zmq
import zmq.asyncio

# --------------------------- CONFIG ---------------------------
# Get a free access key from https://console.picovoice.ai/
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY", "YOUR_ACCESS_KEY")
# Put the .ppn file for your wake word (e.g., hey_jarvis.ppn) in this folder
PORCUPINE_KEYWORD_PATHS = ["hey_jarvis.ppn"]

# Vosk model – download from https://alphacephei.com/vosk/models
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"

# Coqui TTS – a lightweight English voice
TTS_MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC"

# ZeroMQ endpoint of the core service (REQ/REP)
ZMQ_ENDPOINT = "tcp://localhost:5555"

# Audio settings (must match Porcupine/Vosk expectations)
SAMPLE_RATE = 16000
FRAME_LENGTH = 512  # Porcupine processes this many samples per call
# --------------------------------------------------------------


class VoiceAgent:
    def __init__(
        self,
        wake_callback: Callable[[str], None],
        command_callback: Callable[[str], None],
    ):
        self.wake_cb = wake_callback
        self.cmd_cb = command_callback
        self._running = False
        self._loop = asyncio.get_event_loop()

        # ---- Porcupine (wake word) ----
        self.porcupine = pvporcupine.create(
            access_key=PORCUPINE_ACCESS_KEY,
            keyword_paths=[
                os.path.join(os.path.dirname(__file__), p)
                for p in PORCUPINE_KEYWORD_PATHS
            ],
        )

        # ---- Vosk (offline STT) ----
        if not os.path.exists(VOSK_MODEL_PATH):
            print(
                f"[❌] Vosk model not found at {VOSK_MODEL_PATH}. "
                "Download it from https://alphacephei.com/vosk/models and unpack."
            )
            sys.exit(1)
        self.vosk_model = vosk.Model(VOSK_MODEL_PATH)
        self.vosk_rec = vosk.KaldiRecognizer(self.vosk_model, SAMPLE_RATE)

        # ---- Coqui TTS ----
        self.tts = TTS(model_name=TTS_MODEL_NAME, progress_bar=False, gpu=False)

        # ---- ZeroMQ client (REQ) to talk to the core service ----
        self.ctx = zmq.asyncio.Context()
        self.req_socket = self.ctx.socket(zmq.REQ)
        self.req_socket.connect(ZMQ_ENDPOINT)

    # -----------------------------------------------------------------
    # Audio capture thread – runs continuously
    # -----------------------------------------------------------------
    def _audio_loop(self):
        def callback(indata, frames, time, status):
            if status:
                print(f"[⚠] Audio stream status: {status}", file=sys.stderr)

            # Convert float32 [-1,1] → int16 PCM (required by Porcupine/Vosk)
            pcm = (indata[:, 0] * 32768).astype(np.int16).tobytes()

            # 1️⃣ Wake‑word detection
            keyword_index = self.porcupine.process(pcm)
            if keyword_index >= 0:
                self._loop.call_soon_threadsafe(self.wake_cb, "hey_jarvis")
                # After a wake word we listen for a command for a few seconds
                self._listen_for_command(pcm)
                # Reset Vosk for the next utterance
                self.vosk_rec.Reset()

        # Open mic stream
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=0,
            dtype="float32",
            channels=1,
            callback=callback,
        ):
            while self._running:
                time.sleep(0.1)

    def _listen_for_command(self, first_chunk: bytes):
        """
        After the wake word we capture up to `COMMAND_TIMEOUT` seconds of audio,
        feed it to Vosk, and when we get a final hypothesis we invoke the command
        callback.
        """
        COMMAND_TIMEOUT = 5.0  # seconds
        end_time = time.time() + COMMAND_TIMEOUT
        phrase_parts = [first_chunk]

        def audio_callback(indata, frames, time, status):
            if time.inputBufAdcTime > end_time:
                raise sd.CallbackStop
            pcm = (indata[:, 0] * 32768).astype(np.int16).tobytes()
            phrase_parts.append(pcm)

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=0,
            dtype="float32",
            channels=1,
            callback=audio_callback,
        ):
            while time.time() < end_time:
                time.sleep(0.05)

        data = b"".join(phrase_parts)
        if self.vosk_rec.AcceptWaveform(data):
            result = json.loads(self.vosk_rec.Result())
            text = result.get("text", "").strip()
            if text:
                self._loop.call_soon_threadsafe(self.cmd_cb, text)
        # else: ignore partial results for simplicity

    # -----------------------------------------------------------------
    # Public lifecycle
    # -----------------------------------------------------------------
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._thread.start()
        print("[🎤] Voice agent started – say the wake word…")

    def stop(self):
        self._running = False
        if hasattr(self, "_thread"):
            self._thread.join(timeout=2)
        self.porcupine.delete()
        print("[🛑] Voice agent stopped.")

    # -----------------------------------------------------------------
    # TTS – speak text in a background thread (non‑blocking)
    # -----------------------------------------------------------------
    def speak(self, text: str):
        def _tts_thread():
            wav = self.tts.tts(text)
            wav_np = np.array(wav, dtype=np.float32)
            sd.play(
                wav_np,
                samplerate=self.tts.synthesizer.output_sample_rate,
            )
            sd.wait()  # block until playback finishes

        threading.Thread(target=_tts_thread, daemon=True).start()

    # -----------------------------------------------------------------
    # RPC helper – call a method on the core service and get the JSON reply
    # -----------------------------------------------------------------
    async def _call_core(self, method: str, params: dict) -> dict:
        request = {"jsonrpc": "2.0", "method": method, "params": params, "id": "voice"}
        await self.req_socket.send_string(json.dumps(request))
        reply = await self.req_socket.recv_string()
        return json.loads(reply)

    # -----------------------------------------------------------------
    # Callbacks that wire voice → core
    # -----------------------------------------------------------------
    async def _on_wake(self, word: str):
        print(f"[👂] Wake word detected: {word}")
        self.speak("Yes, sir.")  # short acknowledgment

    async def _on_command(self, transcript: str):
        print(f"[🗣] Heard: {transcript}")

        # 1️⃣ Ask the planner for a task list
        plan_resp = await self._call_core("plan_goal", {"goal": transcript})
        if not plan_resp.get("ok"):
            self.speak(f"Sorry, I couldn’t understand that: {plan_resp.get('error')}")
            return

        plan = plan_resp["result"]["plan"]
        # 2️⃣ Optional: let the critic vet the plan (helps catch unsafe ideas)
        critique_resp = await self._call_core("critique", {"plan": plan})
        if critique_resp.get("ok") and not critique_resp["result"].get("approved", True):
            issues = "; ".join(critique_resp["result"].get("issues", []))
            suggestions = "; ".join(critique_resp["result"].get("suggestions", []))
            self.speak(
                f"I’m not sure I should do that. Issues: {issues}. Suggestions: {suggestions}"
            )
            return

        # 3️⃣ Execute each task in order (you could also feed them to the Decision Engine)
        for task in plan:
            exec_resp = await self._call_core(
                "execute_task",
                {
                    "task_desc": {
                        "title": task["title"],
                        "description": task.get("description", ""),
                        "priority": task.get("priority", 2),
                    }
                },
            )
            if not exec_resp.get("ok"):
                self.speak(f"Failed to execute {task['title']}: {exec_resp.get('error')}")
                break
            else:
                # Optionally speak a short confirmation
                self.speak(f"{task['title']} completed.")

        # 4️⃣ Store an episode so the assistant can recall what it just did
        await self._call_core(
            "memory_episode",
            {
                "event_type": "user_command_executed",
                "data": {"command": transcript, "plan": plan},
                "importance": 0.7,
                "tags": ["user", "command"],
            },
        )
        self.speak("All done, sir.")

# -----------------------------------------------------------------
# Entry point – glue everything together
# -----------------------------------------------------------------
def main():
    def wake_callback(word):
        # The voice agent runs its own asyncio loop; we schedule the coroutine.
        asyncio.run_coroutine_threadsafe(va._on_wake(word), va._loop)

    def command_callback(text):
        asyncio.run_coroutine_threadsafe(va._on_command(text), va._loop)

    va = VoiceAgent(wake_callback=wake_callback, command_callback=command_callback)
    try:
        va.start()
        # Keep the main thread alive until Ctrl‑C
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[⏹] Shutting down…")
    finally:
        va.stop()

if __name__ == "__main__":
    main()