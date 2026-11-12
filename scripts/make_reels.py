import json
import os
import subprocess

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input" / "reels.json"
CHARACTER = ROOT / "assets" / "character.png"
OUT = ROOT / "output"
WORK = ROOT / "work"
W, H = 1080, 1920
VOICE = "ko-KR-SunHiNeural"

def run(cmd):
    subprocess.run(cmd, check=True)

def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()

def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def make_frame(character, label, headline, subtitle, index, total):
    im = Image.new("RGB", (W, H), (7, 18, 45))
    d = ImageDraw.Draw(im)

    # Newsroom-style blue gradient and decorative market lines
    for y in range(H):
        t = y / H
        color = (int(8 + 5*t), int(28 + 15*t), int(70 + 25*t))
        d.line((0, y, W, y), fill=color)
    d.ellipse((700, 100, 1320, 720), outline=(22, 100, 190), width=5)
    d.ellipse((760, 160, 1260, 660), outline=(15, 75, 145), width=3)
    d.line([(680, 600), (790, 520), (870, 550), (960, 390), (1080, 280)], fill=(30, 190, 245), width=10)

    d.text((64, 62), "ECONOMY NEWS", font=font(42, True), fill=(210, 230, 255))
    rounded(d, (64, 135, 1016, 220), 28, (15, 75, 155))
    d.text((96, 153), label, font=font(38, True), fill=(255, 255, 255))

    # Character portrait
    cw, ch = character.size
    target_w = 790
    target_h = int(ch * target_w / cw)
    portrait = character.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if target_h > 890:
        top = (target_h - 890) // 2
        portrait = portrait.crop((0, top, target_w, top + 890))
        target_h = 890
    x = (W - target_w) // 2
    y = 255
    rounded(d, (x-8, y-8, x+target_w+8, y+target_h+8), 34, (12, 45, 95), outline=(55, 150, 235), width=5)
    im.paste(portrait, (x, y))
    d = ImageDraw.Draw(im)

    # Headline and subtitle cards
    rounded(d, (54, 1190, 1026, 1510), 36, (5, 23, 58), outline=(45, 145, 230), width=4)
    lines = textwrap.wrap(headline, width=18)
    yy = 1230
    for line in lines[:3]:
        d.text((90, yy), line, font=font(66, True), fill=(255, 220, 65), stroke_width=2, stroke_fill=(0, 0, 0))
        yy += 88

    rounded(d, (54, 1540, 1026, 1770), 30, (238, 245, 255))
    sub_lines = textwrap.wrap(subtitle, width=26)
    yy = 1580
    for line in sub_lines[:3]:
        d.text((90, yy), line, font=font(39, False), fill=(14, 30, 58))
        yy += 55

    d.text((64, 1820), f"매일 30초 경제 브리핑  •  {index}/{total}", font=font(32, True), fill=(210, 230, 255))
    return im

def make_audio(text, path, voice=None):
    tts = gTTS(text=text, lang="ko")
    tts.save(str(path))

def probe_duration(path):
    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(result)

def main():
    if not INPUT.exists():
        raise FileNotFoundError("input/reels.json 파일이 없습니다.")
    if not CHARACTER.exists():
        raise FileNotFoundError("assets/character.png 파일이 없습니다. 캐릭터 이미지를 업로드하세요.")

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    news = data.get("news", [])
    if not news:
        raise ValueError("reels.json의 news 배열이 비어 있습니다.")

    voice = data.get("voice", VOICE)
    scenes = [
        (data.get("title", "오늘의 경제 뉴스"), data.get("hook", "오늘의 주요 경제 소식을 전해드립니다."), "오늘의 경제 뉴스")
    ]
    for item in news[:3]:
        scenes.append((
            item.get("headline", "경제 뉴스"),
            item.get("summary", ""),
            item.get("headline", "오늘의 핵심 뉴스")
        ))
    scenes.append((
        "내일도 함께해요!",
        data.get("closing", "도움이 되셨다면 팔로우해 주세요."),
        "오늘의 경제 브리핑"
    ))

    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    character = Image.open(CHARACTER).convert("RGB")
    segments = []

    for i, (headline, spoken, label) in enumerate(scenes, start=1):
        audio = WORK / f"voice_{i:02d}.mp3"
        frame = WORK / f"frame_{i:02d}.png"
        segment = WORK / f"segment_{i:02d}.mp4"

        make_audio(spoken, audio, voice)
        make_frame(character, label, headline, spoken, i, len(scenes)).save(frame)
        duration = probe_duration(audio) + 0.35

        run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-i", str(frame), "-i", str(audio),
            "-vf", "scale=1080:1920,format=yuv420p",
            "-t", str(duration), "-r", "30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            str(segment)
        ])
        segments.append(segment)

    concat_file = WORK / "concat.txt"
    concat_file.write_text("".join(f"file '{p.resolve()}'\n" for p in segments), encoding="utf-8")
    final = OUT / "reels.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", "-movflags", "+faststart", str(final)
    ])
    print(f"릴스 생성 완료: {final}")

if __name__ == "__main__":
    main()
