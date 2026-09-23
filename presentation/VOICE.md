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
ffmpeg -i work\final-narration.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:a aac -b:a 160k work\final-narration.m4a
```

The renderer rejects unfinished narration, overlapping speech, or speech running past the 180-second timeline. Review the generated `.timings.json`; leave a few seconds of visual silence around each proof point. Listen to the full final mix for pronunciation, unnatural emphasis, clipping, and pace before embedding it in the MP4. A local opening-line test rendered and passed format/duration checks; its voice quality still needs a human listen. The final MP4 and Bob-specific narration do not exist yet.
