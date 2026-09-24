# Demo narration — pre-event setup

The final three-minute video should use one warm, human-sounding neural voice, at a measured pace. Pause at the failing SQL replay and at the actual Bob task summary. Do not read code aloud or rush the numbers. The final script must describe the observed Bob session and independent replay, not the planned outcome.

The local renderer uses [Kokoro 82M](https://huggingface.co/hexgrad/Kokoro-82M) and [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), with `af_heart` at speed `0.82` by default. The script can set a slower `speed` for an individual segment; the opening uses `0.72` and the counterexample uses `0.76` so judges have more time to read the visible evidence. The model card lists Apache 2.0 weights; the ONNX wrapper is MIT licensed. The official voice list grades `af_heart` highest among its American English choices. This is pre-event media preparation, not an IBM Bob contribution.

The three Bob-specific slots now use `0.76` too. A private timing-only render with neutral, explicitly non-event text measured 55 words in 27.81 seconds, 45 in 21.16 seconds, and 29 in 14.46 seconds. Their slots are 39, 28, and 21 seconds, leaving room to read the real Bob summary and replay. A full 180-second timing render ended its final spoken line at 179.25 seconds without overlap. These measurements guide length only: write the final Bob lines from observed evidence, rerender, and review the actual timings and voice quality before submission. The timing-only WAV must never be submitted.

The model and voices are not in Git. Download the v1.0 English files from the [wrapper's model-files-v1.1 release](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1) into `work/voice-model/`. The release SHA-256 values are:

| File | SHA-256 |
| --- | --- |
| `kokoro-v1.0.onnx` | `beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a` |
| `voices-v1.0.bin` | `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d` |

On this Windows host, an isolated Python 3.12 environment with `voice-requirements.txt` has been prepared under ignored `work/voice-venv/`. To recreate it on another Windows host, use Python 3.12:

```powershell
py -3.12 -m venv work\voice-venv
work\voice-venv\Scripts\python.exe -m pip install -r presentation\voice-requirements.txt
```

After Bob's real task, copy `narration.template.json` to `work/final-narration.json`, replace every `PENDING` line with the observed result, adjust clip starts to the actual video, and render:

```powershell
work\voice-venv\Scripts\python.exe presentation\render_voice.py --script work\final-narration.json --output work\final-narration.wav
```

Generate an optional caption file from the measured speech-segment timings, then listen to the final MP4 while reviewing every cue. Sentence boundaries inside a segment are estimated, so adjust any cue that leads or lags the spoken words before uploading it with the video:

```powershell
python presentation\make_captions.py --script work\final-narration.json --timings work\final-narration.timings.json --output work\cutover-demo.srt
```

The pre-event 64-second prologue produced an ignored 11-cue SRT with no overlaps or unfinished text. This is a caption workflow check, not a final video or Bob evidence.

Then copy `video-clips.template.json` to `work/final-video-clips.json`, replace every pending path with an actual screen recording, and adjust trims to show the observed results. The clip durations must total 180 seconds. Assemble the video with the WAV; the assembler normalizes the audio once:

```powershell
python presentation\assemble_video.py --manifest work\final-video-clips.json --narration work\final-narration.wav --output work\cutover-demo.mp4
```

For Cutover web footage, record an isolated headless browser page. It checks the chosen live result and saves a silent, page-only WebM under ignored `work/`. Set the bundled Playwright path on this host, then run:

```powershell
$env:CUTOVER_PLAYWRIGHT_MODULE='C:\Users\JosephMayo\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
node presentation\capture_web_demo.js https://cutover-rehearsal.onrender.com/ work\cutover-direct.webm direct 23
node presentation\capture_web_demo.js https://cutover-rehearsal.onrender.com/ work\cutover-late.webm late 52
```

Inspect frames at the opening, verdict, and execution trace before using the clip. The hosted site can show a blank frame during initial load, so start each final trim after the page is visible. The same recording may appear in multiple clip entries with different `start_sec` values. Public-site draft takes passed the `24 / 92` Direct rename and `108 / 124` Late bridge assertions. The late take pauses on the acknowledged `old.write` before scrolling to the `18 Marina Road` expected versus `4 Broad Street` observed comparison. These are pre-event product footage drafts, not Bob evidence or a finished video. The browser capture is 1280×720; the final assembler scales it to 1920×1080.

For the 22-second window-replay shot, use two 16:9 crops of the same real browser take: first the acknowledged write, then the mismatched read. Review the recorded cue times before rendering; the following values matched one September 23 public take and are not guaranteed for later takes:

```powershell
ffmpeg -hide_banner -loglevel error -i work\cutover-late.webm -filter_complex '[0:v]trim=start=17:duration=6,setpts=PTS-STARTPTS,crop=640:360:640:270,scale=1920:1080,fps=30,tpad=stop_mode=clone:stop_duration=4,format=yuv420p[a];[0:v]trim=start=30:duration=12,setpts=PTS-STARTPTS,crop=640:360:640:210,scale=1920:1080,fps=30,format=yuv420p[b];[a][b]concat=n=2:v=1:a=0[v]' -map '[v]' -c:v libx264 -preset medium -crf 20 -an -n work\cutover-window-proof.mp4
```

The inspected draft segment is 22 seconds of 1920×1080 H.264 and makes both the write order and the expected/observed values readable. Its first six seconds hold for four more seconds so the explanation can finish before the comparison appears. It is an edit of the live rehearsal recording, not a simulated result. Keep the uncropped source for audit and review the entire edited segment before the final assembly.

Record Bob IDE evidence only after the real event-period task, using a recorder scoped to the Bob application window. Check a test frame for unrelated windows, accounts, and tokens before recording the session. Do not use a full-desktop source. Keep raw footage ignored under `work/`, then review and trim every used segment before assembly.

The voice renderer rejects unfinished narration, overlapping speech, or speech running past the 180-second timeline, and reports the conflicting times when a segment does not fit. The video assembler rejects pending clips, missing or too-short recordings, timing mismatches, existing output paths, and a final video at or above the general submission guide's 300 MB limit. It verifies the finished file is 1920×1080 H.264/AAC at 30 frames per second. A four-second test using two synthetic color clips and synthetic audio confirmed the media pipeline and cut order; those test files are ignored and cannot count as demo footage.

The five non-Bob lines in the template were rendered at speed 0.82 as an initial timing rehearsal. The opening and Late bridge cues were moved three and two seconds later to align spoken counts with the visible results. A later 64-second prologue uses the segment speeds above: the opening ends at 16.60 seconds, Late bridge at 34.82, and the counterexample at 60.55, leaving room before each cut. Its measured delivery is about 119, 109, and 120 words per minute respectively. The closing line was shortened to preserve the slower pace; its earlier check ended at 179.26 seconds. The new prologue passed the 1920×1080, 30 fps, H.264/AAC format and duration checks. Subjective voice quality still needs a human listen. This partial render is not the final video; every Bob-specific line still requires observed session evidence and another full-length timing check.

Review the generated `.timings.json`; leave a few seconds of visual silence around each proof point. Watch and listen to the full final MP4 for legibility, pronunciation, unnatural emphasis, clipping, secrets, and pace before publishing. A local opening-line test rendered and passed format/duration checks; its voice quality still needs a human listen. The final MP4 and Bob-specific narration do not exist yet.

For the required video link, prefer an unlisted YouTube upload through an existing channel after the final MP4 is reviewed. [An unlisted link](https://support.google.com/youtube/answer/157177?hl=en) is viewable by judges without a Google account. Test playback from a signed-out browser and confirm the actual event form accepts the URL. If that route is unavailable, use the form's own media upload or a publicly playable MP4 link only after testing it in the form; do not assume a repository file link is accepted. Keep the final link in the submission record.

On September 23, the existing YouTube Studio channel opened signed in and exposed **Upload videos**. This checks channel availability only; no Cutover video has been uploaded, its playback and the event form's URL acceptance remain unverified.
