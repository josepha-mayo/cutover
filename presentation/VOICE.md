# Demo narration — pre-event setup

The final three-minute video should use one warm, human-sounding neural voice, at a measured pace. Pause at the failing SQL replay and at the actual Bob task summary. Do not read code aloud or rush the numbers. The final script must describe the observed Bob session and independent replay, not the planned outcome.

The local renderer uses [Kokoro 82M](https://huggingface.co/hexgrad/Kokoro-82M) and [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), with `af_heart` at speed `0.82` by default. The model card lists Apache 2.0 weights; the ONNX wrapper is MIT licensed. The official voice list grades `af_heart` highest among its American English choices. This is pre-event media preparation, not an IBM Bob contribution.

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

Then copy `video-clips.template.json` to `work/final-video-clips.json`, replace every pending path with an actual screen recording, and adjust trims to show the observed results. The clip durations must total 180 seconds. Assemble the video with the WAV; the assembler normalizes the audio once:

```powershell
python presentation\assemble_video.py --manifest work\final-video-clips.json --narration work\final-narration.wav --output work\cutover-demo.mp4
```

For real footage on this Windows host, FFmpeg has the `gdigrab` desktop source. After hiding private tabs and making the demo text legible, start a silent screen recording during the actual event-period task:

```powershell
ffmpeg -hide_banner -f gdigrab -framerate 30 -i desktop -t 900 -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -n work\raw-session.mkv
```

Press `q` in that terminal to end the recording early. The raw capture stays under ignored `work/`; the same file can appear in multiple clip entries with different `start_sec` values. Inspect and trim out private account or token screens before assembly. `gdigrab` availability was checked, but a real desktop capture has not been made yet.

The voice renderer rejects unfinished narration, overlapping speech, or speech running past the 180-second timeline, and reports the conflicting times when a segment does not fit. The video assembler rejects pending clips, missing or too-short recordings, timing mismatches, existing output paths, and a final video at or above the general submission guide's 300 MB limit. It verifies the finished file is 1920×1080 H.264/AAC at 30 frames per second. A four-second test using two synthetic color clips and synthetic audio confirmed the media pipeline and cut order; those test files are ignored and cannot count as demo footage.

The five non-Bob lines in the template were rendered at speed 0.82 as a timing rehearsal. Their speech ends at 10.96, 32.82, 58.24, 167.02, and 179.26 seconds respectively, with no overlap or overrun. The closing line was shortened to preserve the slower pace. This partial timing render is not the final narration; every Bob-specific line still requires observed session evidence and another full-length timing check.

Review the generated `.timings.json`; leave a few seconds of visual silence around each proof point. Watch and listen to the full final MP4 for legibility, pronunciation, unnatural emphasis, clipping, secrets, and pace before publishing. A local opening-line test rendered and passed format/duration checks; its voice quality still needs a human listen. The final MP4 and Bob-specific narration do not exist yet.

For the required video link, prefer an unlisted YouTube upload through an existing channel after the final MP4 is reviewed. [An unlisted link](https://support.google.com/youtube/answer/157177?hl=en) is viewable by judges without a Google account. Test playback from a signed-out browser and confirm the actual event form accepts the URL. If that route is unavailable, use the form's own media upload or a publicly playable MP4 link only after testing it in the form; do not assume a repository file link is accepted. Keep the final link in the submission record.

On September 23, the existing YouTube Studio channel opened signed in and exposed **Upload videos**. This checks channel availability only; no Cutover video has been uploaded, its playback and the event form's URL acceptance remain unverified.
