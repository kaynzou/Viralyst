# Lesson 4: Understanding a real video

Until now a human wrote the video brief by hand: the hook, the description, and four 0–1 ratings.
Now Viralyst does it from the actual video file:

1. **ffmpeg** pulls out pictures and the soundtrack.
2. **Whisper** (on your Mac) writes down what's said.
3. **Claude** looks at the pictures, reads the transcript, writes the brief, rates the video and
   suggests a stronger opening line.
4. **Supertonic** (on your Mac) can read that opening line out loud, so you can hear it.

```bash
cd backend
uv run scripts/make_sample_video.py        # makes examples/sample_demo.mp4 (free)
uv run analyze_video.py examples/sample_demo.mp4 --out examples/sample_demo.json --voiceover
uv run run.py examples/sample_demo.json    # simulate it like any other example
```

## Map of the new code

| File | What it does |
|---|---|
| `viralyst/media.py` | Runs ffmpeg/ffprobe: video facts, frames, audio |
| `viralyst/speech.py` | Speech-to-text with Whisper, including when each word is said |
| `viralyst/video_analyzer.py` | Sends frames and transcript to Claude, checks the answer, builds the brief |
| `viralyst/voiceover.py` | Text-to-speech with Supertonic |
| `analyze_video.py` | The command that runs all of the above and saves a brief |
| `scripts/make_sample_video.py` | Draws a test video with Pillow and gives it a voice with macOS `say` |
| `tests/test_video.py` | 9 tests, using a generated test video plus fake Whisper, Supertonic and Claude |

## Concept 1: How an AI "watches" a video

Claude reads text and images, not video files. So we show it what a viewer experiences:

- **Frames:** pictures taken at chosen moments (`frame_times`). The first 3 seconds get one every
  half second, because that's when people decide to scroll. After that, about one every 2 seconds
  (at most 10). Choosing a few representative moments instead of every frame is called **sampling**.
- **Labels:** each picture is preceded by "Frame at 1.5s", so Claude knows the order and timing.
- **Size matters:** an image costs roughly (width × height) ÷ 750 tokens, so frames are shrunk to
  512 pixels wide. About 600 tokens each instead of thousands.

The sample video sends 11 frames plus the transcript, for about $0.11 per analysis.

## Concept 2: Running other programs from Python

ffmpeg is a command-line program. `subprocess.run([...])` runs it exactly as if you'd typed it in
the Terminal, and `run()` in `media.py` raises a clear error if it fails. The commands, decoded:

| Command piece | Meaning |
|---|---|
| `ffprobe -show_entries format=duration:stream=codec_type,width,height -of json` | "Tell me the length, size and tracks, as JSON" |
| `-ss 1.5 -i video.mp4 -frames:v 1` | "Jump to 1.5s and save one frame" (`-ss` *before* `-i` jumps instead of playing from the start) |
| `-vf scale=512:-2` | "Resize to 512 wide, keep the shape" (`-2` = matching even height) |
| `-vn -ac 1 -ar 16000` | "No video, one channel (mono), 16,000 samples per second" |

`shutil.which("ffmpeg")` checks whether a program is installed, so you get "brew install ffmpeg"
instead of a cryptic crash.

## Concept 3: Speech-to-text (Whisper)

Whisper is an AI model that turns speech into text. `faster-whisper` runs it **on your Mac**: free,
private (the audio never leaves your computer), and about 4 seconds for the sample video.

- Sound is a list of numbers: 16,000 **samples** per second of air pressure. `soundfile` reads the
  WAV into a numpy array, and Whisper turns those numbers into words.
- **Segments** are chunks of speech ("[0.0–6.8] I had 4200 unread emails, watch this, one click…").
  That's too coarse for the hook, so we also ask for **word timestamps** and compute exactly what's
  said before 3 seconds: *"I had 4200 unread emails, watch this,"*.
- Model sizes: `--whisper tiny` is fastest, `small` most accurate, `base` is the middle.

## Concept 4: Text-to-speech (Supertonic)

Supertonic goes the other way: text in, voice out (10 voices, F1–F5 and M1–M5, 31 languages). We
use it to record Claude's suggested opening line, so you can *hear* the better hook.

A neat test we ran: Supertonic said "Four thousand unread emails. Gone in thirty seconds." Whisper
listened to that audio and wrote "4000 unread emails, gone in 30 seconds." When two independent
tools agree, you can trust both a lot more. That's a **round-trip test**.

## Concept 5: Asking an AI for ratings

"Rate the hook from 0 to 1" alone gives vague, generous numbers. The prompt in `video_analyzer.py`
adds three things:

- **Anchors:** "0.1 = a logo or slow intro, 0.5 = clear but ordinary, 0.9 = an instant surprising
  payoff". Examples at both ends make the scale concrete.
- **A base rate:** "a typical reel scores about 0.5", which fights the "too nice" problem again.
- **Checks afterwards:** `clean()` clamps ratings into 0–1 and keeps only known topic tags, just
  like the audience builder in Lesson 3.

These ratings are still **Claude's opinion**, not a measurement. Checking them against real results
is Phase 6 (calibration).

## Concept 6: When libraries don't get along

The first real Whisper run crashed: `open() got an unexpected keyword argument 'metadata_errors'`.
`faster-whisper` opens audio files with a library called `av`, and `av`'s newest version removed an
option `faster-whisper` still uses. Both are fine on their own; together they clash.

The fix wasn't to downgrade anything. We already had ffmpeg producing a clean WAV, so we read it with
`soundfile` and hand Whisper the raw numbers. The broken code path is simply never used. Reading the
error carefully (which library, which line, which argument) pointed straight at the fix.

## Concept 7: Testing code that needs videos and AI models

- **Generate test data:** ffmpeg can *create* a video (`-f lavfi -i testsrc2=…` plus a sine-wave
  beep), so tests don't need a real video file checked into the project.
- **`@pytest.mark.skipif`:** media tests skip politely on a computer without ffmpeg.
- **Fakes again:** a fake Whisper, a fake Supertonic and a fake Claude test our logic in milliseconds,
  for free.
- **Fixture `scope="module"`:** the test video is made once and shared by every test in the file.

## Python you used in this phase

- **`subprocess.run(command, capture_output=True, text=True)`:** run a program and read its output.
- **`tempfile.TemporaryDirectory()`:** a scratch folder that deletes itself when the `with` block ends.
- **`base64`:** turns binary data (a JPEG) into plain text, so it can travel inside JSON.
- **Lazy imports:** `from faster_whisper import WhisperModel` *inside* the function, so programs that
  never transcribe don't pay its loading time.
- **Generators and `list()`:** Whisper's `segments` is lazy, and work only happens as you read it.
  `list(segments)` makes it all happen at once.

## Exercises

1. **Make and watch the sample.** `uv run scripts/make_sample_video.py`, then open
   `examples/sample_demo.mp4`.
2. **A worse opener.** In `make_sample_video.py`, change `SCRIPT` to start with "Hi, I'm the founder of
   TaskFlow, and today I want to show you…". Make the video again. With a key, analyze both and compare
   `hook_strength`.
3. **Whisper sizes.** Time `--whisper tiny` against `--whisper small` on the same video. Is the bigger
   model worth it?
4. **With a key:** analyze the sample with `--voiceover` and listen to `examples/sample_demo.hook.wav`.
5. **With a key, the real thing:** analyze one of your own reels, then simulate it with `--runs 200`.
   Copy the JSON, replace the `hook` with Claude's `better_hook`, and compare the odds.

## What isn't solved yet

- **Ratings are opinions** until checked against real performance (Phase 6).
- **Frames miss things:** motion, music and tone of voice aren't fully captured by stills plus a transcript.
- **The voiceover is separate:** Supertonic makes an audio file. Mixing it into the video with ffmpeg
  would be a nice next step.
- **Whisper can mishear** product names. Bigger models help.
