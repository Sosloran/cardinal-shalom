"""
Genera 2 imaxes de preview para a demo externa de Cardinal Shalom.
Usa Pollinations (libre, sen clave) — non deriva de app.py nin database.py.
"""
import os
import urllib.request
import urllib.parse
import time

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

OUT_DIR = r"C:\Users\Usuario\AppData\Local\hermes\cache\images"
os.makedirs(OUT_DIR, exist_ok=True)


def fetch_image(prompt, outfile, timeout=30):
    """Pollinations: genera imaxe PNG desde descrición de texto."""
    base_url = "https://image.pollinations.ai/prompt"
    params = urllib.parse.urlencode({
        "prompt": prompt,
        "width": 1024,
        "height": 768,
        "nologo": "true",
        "nofeed": "true",
        "lock_text": "true",
        "seed": str(int(time.time())),
    })
    url = f"{base_url}?{params}"

    print(f"  Fetching: {url[:80]}...")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if len(data) < 1000:
                print(f"  ✗ Pequena resposta ({len(data)} bytes)")
                return None
            with open(outfile, "wb") as f:
                f.write(data)
            size = os.path.getsize(outfile)
            print(f"  ✓ {os.path.basename(outfile)} ({size} bytes)")
            return outfile
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return None


def ensure_png_with_pillow(filepath):
    """Converte/valida a imaxe como PNG usando Pillow se está dispoñible."""
    if not PIL_AVAILABLE:
        return
    try:
        with Image.open(filepath) as img:
            if img.format != "PNG":
                outfile = os.path.splitext(filepath)[0] + ".png"
                img.save(outfile, "PNG")
                if outfile != filepath:
                    os.remove(filepath)
                    print(f"  Convertido a PNG: {os.path.basename(outfile)}")
            else:
                print(f"  PNG válida: {os.path.basename(filepath)}")
    except Exception as e:
        print(f"  Advertencia Pillow: {e}")


if __name__ == "__main__":
    print("=== Xeración de imaxes de preview — Cardinal Shalom ===")
    print(f"Directorio de saída: {OUT_DIR}\n")

    prompts = [
        (
            "login_cardinal_shalom",
            "modern dark educational login page, deep navy blue gradient background, "
            "Cardinal Shalom logo, clean central form, subtle animated blue particle background, "
            "glass card effect, elegant typography, white accents, professional EdTech aesthetic, "
            "soft blue glow, minimalist UI, 3d render style",
        ),
        (
            "dashboard_cardinal_shalom",
            "modern educational dashboard UI, deep navy blue header with white text, "
            "Cardinal Shalom branding, student cards showing grades and portfolio stats, "
            "recent activity feed, progress bars, clean data tables, blue and white color palette, "
            "sidebar navigation, soft ambient blue particles, glassmorphism cards, "
            "EdTech SaaS design, professional screen capture",
        ),
    ]

    generated = []
    for slug, prompt in prompts:
        outfile = os.path.join(OUT_DIR, f"{slug}.png")
        result = fetch_image(prompt, outfile)
        if result:
            generate_preview = True
            ensure_png_with_pillow(result)
            generated.append((slug, prompt, result))

    print(f"\n=== Xeradas {len(generated)} de {len(prompts)} imaxes ===")
    for slug, prompt, filepath in generated:
        print(f"  • {slug}: {filepath}")

    if not generated:
        print("\nAviso: non se xeraron imaxes. Podes querer probar manualmente usando:")
        print("  https://image.pollinations.ai/prompt/{prompt}")
