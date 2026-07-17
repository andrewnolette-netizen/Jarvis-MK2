#!/usr/bin/env bash
# --------------------------------------------------------------
# run_jarvis.sh
# Launch the three processes (core service, voice I/O, GUI HUD)
# in the background and wait for any of them to exit.
# --------------------------------------------------------------
set -e

echo "🚀 Starting JARVIS‑MK2 full stack…"

# 1️⃣ Core service (RPC on 5555, PUB/SUB on 5556)
python3 -m jarvis_core.service &
CORE_PID=$!
echo "   Core service PID: $CORE_PID"

# 2️⃣ Voice I/O (wake word + STT/TTS)
python3 -m voice_io.voice_agent &
VOICE_PID=$!
echo "   Voice agent PID: $VOICE_PID"

# 3️⃣ GUI HUD
python3 -m gui.main_window &
GUI_PID=$!
echo "   GUI PID: $GUI_PID"

# Trap SIGINT/SIGTERM to shut everything down cleanly
trap "echo '🛑 Shutting down…'; kill $CORE_PID $VOICE_PID $GUI_PID 2>/dev/null; wait" SIGINT SIGTERM

# Wait for any child to exit (if one crashes we’ll still clean up)
wait -n