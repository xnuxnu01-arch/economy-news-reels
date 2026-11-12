# Economy News Reels

Automated Korean economy-news reel builder.

## Files
- `assets/character.png`: fixed presenter image
- `input/reels.json`: narration and on-screen news text
- `scripts/make_reels.py`: TTS + image/video composition
- `output/reels.mp4`: generated vertical video

## Run
GitHub Actions → Build Economy Reel → Run workflow.

The workflow uses Edge TTS (online service; no API key configured) and FFmpeg.
Voice service availability and free access can change. Review generated news facts
before publishing; this starter workflow does not independently verify news claims.
