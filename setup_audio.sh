#!/usr/bin/env bash
# Creates the "MeetingOut" virtual sink and loops it to your headphones.
# Usage:
#   bash setup_audio.sh                 # use current default sink as headphones
#   bash setup_audio.sh <sink_name>     # pick a sink from: pactl list short sinks
#   bash setup_audio.sh --route         # move playing browser audio into MeetingOut
#   bash setup_audio.sh --undo          # remove everything this script added
set -euo pipefail

STATE="$HOME/.cache/interp-audio-modules"
mkdir -p "$(dirname "$STATE")"

if [ "${1:-}" = "--undo" ]; then
  if [ -f "$STATE" ]; then
    while read -r id; do pactl unload-module "$id" 2>/dev/null || true; done < "$STATE"
    rm -f "$STATE"
    echo "Removed MeetingOut sink and loopback."
  else
    echo "Nothing to undo."
  fi
  exit 0
fi

if [ "${1:-}" = "--route" ]; then
  # Move playing browser/Teams streams into MeetingOut (they only exist while playing).
  # PipeWire remembers the choice per app, so later streams usually go there too.
  APPS="${2:-chrome|chromium|firefox|teams|edge|brave|opera|vivaldi}"
  moved=$(pactl -f json list sink-inputs | python3 -c '
import json, re, sys
apps = re.compile(sys.argv[1], re.I)
for s in json.load(sys.stdin):
    p = s["properties"]
    who = " ".join(str(p.get(k, "")) for k in ("application.name", "application.process.binary"))
    if apps.search(who):
        print(s["index"], p.get("application.name") or p.get("application.process.binary"))
' "$APPS")
  if [ -z "$moved" ]; then
    echo "No browser audio playing. Start the video/meeting audio first, then run this again."
    exit 1
  fi
  while read -r idx name; do
    pactl move-sink-input "$idx" meeting_out && echo "Moved '$name' to MeetingOut"
  done <<< "$moved"
  exit 0
fi

if pactl list short sinks | awk '{print $2}' | grep -qx meeting_out; then
  echo "meeting_out already exists. Run with --undo first to recreate it."
  exit 0
fi

HEADPHONES="${1:-$(pactl get-default-sink)}"
if ! pactl list short sinks | awk '{print $2}' | grep -qx "$HEADPHONES"; then
  echo "Sink '$HEADPHONES' not found. Available sinks:"
  pactl list short sinks
  exit 1
fi

SINK_ID=$(pactl load-module module-null-sink sink_name=meeting_out \
  sink_properties=device.description=MeetingOut)
LOOP_ID=$(pactl load-module module-loopback source=meeting_out.monitor \
  sink="$HEADPHONES" latency_msec=50)
printf '%s\n%s\n' "$LOOP_ID" "$SINK_ID" > "$STATE"

# Keep headphones as the default so other apps (and the TTS) stay there.
pactl set-default-sink "$HEADPHONES"

echo "$HEADPHONES" > "$HOME/.cache/interp-headphone-sink"
echo "OK"
echo "  Headphones sink : $HEADPHONES"
echo "  Capture source  : meeting_out.monitor"
echo
echo "Now start the meeting/video audio and run: make route"
echo "(or in pavucontrol -> Playback, set your browser to 'MeetingOut')"
echo "Tip: lower the 'Loopback' stream there so the English voice is louder than the German."
