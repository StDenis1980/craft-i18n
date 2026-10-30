# Build the narrated "Tinta Office: overview" videos from per-scene clips.
#
#   python build_overview.py es uk va
#
# Expects clips/<lang>/<scene>.mp4 (scenes listed in narr.SCENES) next to this script, and
# AZURE_SPEECH_KEY / AZURE_SPEECH_REGION in the environment. Writes out/tinta-office-overview-<lang>-youtube.mp4
# (no burned-in captions) and the matching .<lang>.srt. Each scene is held on its last frame while the
# narration is longer than the clip, and trimmed when the clip runs well past the narration.
import os, re, subprocess, sys, urllib.request
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from narr import NARR, SCENES

VOICE = {"es": os.environ.get("AZURE_VOICE_ES", "es-ES-AlvaroNeural"),
         "uk": os.environ.get("AZURE_VOICE_UK", "uk-UA-OstapNeural"),
         "va": os.environ.get("AZURE_VOICE_VA", "ca-ES-EnricNeural")}
LOCALE = {"es": "es-ES", "uk": "uk-UA", "va": "ca-ES"}
SRT_LANG = {"es": "es", "uk": "uk", "va": "ca"}
LEAD = 0.4   # silence before each scene's narration
TAIL = 1.0   # minimum picture after the narration ends
SLACK = 8.0  # most picture kept after the narration ends (keeps each scene's actions whole)


def tts(lang, text, wav):
    region = os.environ.get("AZURE_SPEECH_REGION", "northeurope")
    ssml = (f'<speak version="1.0" xml:lang="{LOCALE[lang]}"><voice name="{VOICE[lang]}">'
            f'<prosody rate="{os.environ.get("AZURE_RATE", "0%")}">{escape(text)}</prosody></voice></speak>')
    req = urllib.request.Request(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1", data=ssml.encode("utf-8"),
        headers={"Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"], "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm", "User-Agent": "tinta-video"})
    with urllib.request.urlopen(req, timeout=60) as r, open(wav, "wb") as f:
        f.write(r.read())


def run(*a):
    subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).decode())


def srt_ts(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def sentences(text):
    """Caption-sized pieces: split at sentence ends, then at colons when a piece is long."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        if len(s) > 90 and ": " in s:
            a, b = s.split(": ", 1)
            out += [a + ":", b]
        else:
            out.append(s)
    return [s for s in out if s]


def build(lang):
    clips = os.path.join(HERE, "clips", lang)
    work = os.path.join(HERE, "work", lang)
    out = os.path.join(HERE, "out")
    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    parts, cues, at = [], [], 0.0
    for n, scene in enumerate(SCENES):
        clip = os.path.join(clips, scene + ".mp4")
        wav = os.path.join(work, f"{n:02d}.wav")
        tts(lang, NARR[lang][scene], wav)
        speech = dur(wav)
        clip_len = dur(clip)
        length = max(LEAD + speech + TAIL, min(clip_len, LEAD + speech + SLACK))
        hold = max(0.0, length - clip_len)
        seg = os.path.join(work, f"{n:02d}.mp4")
        vf = f"tpad=stop_mode=clone:stop_duration={hold:.2f}" if hold > 0 else "null"
        run("ffmpeg", "-y", "-i", clip, "-i", wav,
            "-filter_complex", f"[0:v]{vf},fps=30[v];[1:a]adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "1", seg)
        # Captions: the scene's sentences, timed in proportion to their length.
        pieces = sentences(NARR[lang][scene])
        total = sum(len(p) for p in pieces) or 1
        t = at + LEAD
        for p in pieces:
            d = speech * len(p) / total
            cues.append((t, t + d, p))
            t += d
        parts.append(seg)
        at += dur(seg)
        print(f"{lang} {scene}: speech {speech:.1f}s, clip {clip_len:.1f}s -> {length:.1f}s")
    lst = os.path.join(work, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    name = os.path.join(out, f"tinta-office-overview-{lang}-youtube")
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", name + ".mp4")
    with open(f"{name}.{SRT_LANG[lang]}.srt", "w", encoding="utf-8") as f:
        for i, (a, b, text) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_ts(a)} --> {srt_ts(b)}\n{text}\n\n")
    print(f"{name}.mp4: {dur(name + '.mp4'):.1f}s")


if __name__ == "__main__":
    for lang in sys.argv[1:] or ["es", "uk", "va"]:
        build(lang)
