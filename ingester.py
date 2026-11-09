from pathlib import Path
import subprocess
import numpy as np
import render
import domain

FFMPEG_BIN = Path(__file__).parent / "dep" / "ffmpeg" / "ffmpeg.exe"

# each frame is shrunk to this size (area average) before looking for its brightest pixel,
# so a single noisy/highlight pixel doesn't win; 64x36 keeps 16:9 and divides 1920x1080 exactly
SAMPLE_W = 64
SAMPLE_H = 36

FRAME_SIZE = SAMPLE_W * SAMPLE_H * 3   # rgb24
CHUNK_FRAMES = 2000                    # frames processed per numpy batch (~14 MB)

# Rec. 709 luma weights, "brightness" as perceived by the eye
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

def _frames_stats(raw : bytes) -> tuple[np.ndarray, np.ndarray]:
    # raw holds n whole frames of SAMPLE_W x SAMPLE_H rgb24 pixels
    n = len(raw) // FRAME_SIZE

    pixels = np.frombuffer(raw, dtype=np.uint8, count=n * FRAME_SIZE).reshape(n, SAMPLE_W * SAMPLE_H, 3)

    avg = np.rint(pixels.mean(axis=1)).astype(np.uint8)

    luma = pixels.astype(np.float32) @ LUMA
    bright = pixels[np.arange(n), luma.argmax(axis=1)]

    return avg, bright

def ingest_frames(file_path) -> tuple[list[domain.Color], list[domain.Color]]:
    # returns (average colors, brightest colors), one of each per frame, from a single ffmpeg pass
    cmd = [
        str(FFMPEG_BIN),
        "-v", "error",
        "-i", str(file_path),
        "-an",                                              # ignore audio
        "-vf", f"scale={SAMPLE_W}:{SAMPLE_H}:flags=area",   # small version of each frame
        "-pix_fmt", "rgb24",
        "-f", "rawvideo",
        "pipe:1",
    ]

    avg_colors : list[domain.Color] = []
    bright_colors : list[domain.Color] = []

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        assert proc.stdout is not None

        while raw := proc.stdout.read(FRAME_SIZE * CHUNK_FRAMES):
            avg, bright = _frames_stats(raw)

            avg_colors.extend(domain.Color(int(r), int(g), int(b)) for r, g, b in avg)
            bright_colors.extend(domain.Color(int(r), int(g), int(b)) for r, g, b in bright)

        stderr = proc.stderr.read() if proc.stderr else b""

        if proc.wait() != 0:
            raise RuntimeError(stderr.decode(errors="replace"))

    return avg_colors, bright_colors

def ingest(file_path) -> list[domain.Color]:
    # average color of each frame
    avg_colors, _ = ingest_frames(file_path)

    return avg_colors

def ingest_brightest(file_path) -> list[domain.Color]:
    # brightest color of each frame
    _, bright_colors = ingest_frames(file_path)

    return bright_colors

if __name__ == "__main__":
    file_path = r"D:\Videos\Movies\[MTBB] Mushoku Tensei (BD 1080p)\[MTBB] Mushoku Tensei - 01v3 [0C3C916A].mkv"
    #file_path = r"D:\Videos\Movies\Black Swan (2010) [1080p] [BluRay] [5.1] [YTS.MX]\Black.Swan.2010.1080p.BluRay.x264.AAC5.1-[YTS.MX].mp4"

    data : list[domain.Color] = ingest_brightest(file_path)

    #img = render.render(data, 1920, 1080)
    img = render.render_force_max_lines(data, 5, 5000)

    img.show()
