"""生成博客水墨背景图（1920x1080 PNG）。

三套画面共用「生宣纸底 → 淡墨晕染 → 焦墨细节 → 哑光颗粒」的绘制流程，
只调整构图、色相与留白位置：

  1. home-bg.jpg   高远山水：巍峨群山、云海、飞瀑、苍松；中央让位 4:3 入口框。
  2. travel-bg.jpg 青绿水墨：远山淡墨、中景石青石绿、水面留白倒影；右侧大面积留白。
  3. skills-bg.jpg 文人极简：左侧一道焦墨竖笔 + 墨点飞白 + 隐约笔记横线；80% 留白。

配色遵守「焦浓重淡清」：最深处约 #262622，最亮处约 #f7f4ec，
全图不含纯黑 #000000 与纯白 #FFFFFF。修改后重跑本脚本即可再生成。
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

W, H = 1920, 1080
OUT_DIR = Path(__file__).resolve().parent.parent / "public" / "images"

# ── 色板 ────────────────────────────────────────────────────────────
PAPER_WARM = (245, 240, 229)      # 暖宣纸（主页、旅行）
PAPER_COOL = (246, 244, 238)      # 中性宣纸（技能）
INK_DEEP = (38, 38, 34)           # 焦墨
INK_DARK = (58, 59, 52)           # 浓墨
INK_MID = (92, 95, 85)            # 重墨
INK_LIGHT = (142, 144, 130)       # 淡墨
MINERAL_TEAL = (104, 137, 126)    # 石青
MINERAL_GREEN = (120, 146, 116)   # 石绿


# ════════════════════════ 基础工具 ════════════════════════

def sstep(a: float, b: float, x: float) -> float:
    """smoothstep；a>b 时自动反向。"""
    if a == b:
        return 1.0 if x >= b else 0.0
    t = (x - a) / (b - a)
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def profile(stops: list[tuple[float, float]]) -> list[float]:
    """按 [(x, 0..1)] 控制点插值出全宽包络，返回 0..1 列表。"""
    stops = sorted(stops)
    out: list[float] = []
    for x in range(W):
        if x <= stops[0][0]:
            v = stops[0][1]
        elif x >= stops[-1][0]:
            v = stops[-1][1]
        else:
            v = stops[-1][1]
            for (x0, v0), (x1, v1) in zip(stops, stops[1:]):
                if x0 <= x <= x1:
                    t = (x - x0) / (x1 - x0) if x1 != x0 else 1.0
                    t = t * t * (3 - 2 * t)
                    v = v0 + (v1 - v0) * t
                    break
        out.append(max(0.0, min(1.0, v)))
    return out


def hgrad_from(values: list[float]) -> Image.Image:
    """1px 高、全宽的横向遮罩。"""
    g = Image.new("L", (W, 1))
    g.putdata([int(max(0, min(255, v * 255))) for v in values])
    return g.resize((W, H), Image.Resampling.NEAREST)


def vgrad_mask(stops: list[tuple[float, float]]) -> Image.Image:
    """竖向遮罩，stops 为 [(y, 0..1)]。"""
    g = Image.new("L", (1, H))
    vals = []
    for y in range(H):
        v = stops[-1][1]
        for (y0, v0), (y1, v1) in zip(stops, stops[1:]):
            if y0 <= y <= y1:
                t = (y - y0) / (y1 - y0) if y1 != y0 else 1.0
                t = t * t * (3 - 2 * t)
                v = v0 + (v1 - v0) * t
                break
        vals.append(int(max(0, min(255, v * 255))))
    g.putdata(vals)
    return g.resize((W, H), Image.Resampling.NEAREST)


def layer(color: tuple[int, int, int], mask: Image.Image) -> Image.Image:
    lay = Image.new("RGBA", (W, H), (*color, 255))
    lay.putalpha(mask)
    return lay


def comp(base: Image.Image, top: Image.Image) -> Image.Image:
    return Image.alpha_composite(base, top)


def fractal_ridge(n: int, rng: random.Random, rough: float = 0.72) -> list[float]:
    """中点位移法生成 0..1 的山脊线。"""
    ys = [rng.uniform(0.2, 0.8), rng.uniform(0.2, 0.8)]
    scale = rough
    while len(ys) < n:
        new = [ys[0]]
        for i in range(len(ys) - 1):
            a, b = ys[i], ys[i + 1]
            new.append((a + b) / 2 + rng.uniform(-scale, scale))
            new.append(b)
        ys = new
        scale *= 0.55
    lo, hi = min(ys), max(ys)
    span = (hi - lo) or 1.0
    return [(v - lo) / span for v in ys]


def ridge_points(
    seed: int,
    y_base: float,
    amp: float,
    rough: float = 0.72,
    segments: int = 513,
    taper: float = 0.18,
) -> list[tuple[int, float]]:
    """山脊折线：主脊 + 高频细节，峰峦自然，两端略收。"""
    rng = random.Random(seed)
    ys = fractal_ridge(segments, rng, rough=rough)
    detail = fractal_ridge(segments, rng, rough=0.35)
    pts = []
    for i, (v, d) in enumerate(zip(ys, detail)):
        x = W * i / (segments - 1)
        edge = min(1.0, x / (W * taper), (W - x) / (W * taper))
        height = amp * (0.28 + 0.64 * v + 0.08 * d) * (0.55 + 0.45 * edge)
        pts.append((int(x), y_base - height))
    return pts


def ridge_with_peaks(
    seed: int,
    y_base: float,
    amp: float,
    peaks: list[tuple[float, float, float]],
    rough: float = 0.55,
) -> list[tuple[int, float]]:
    """在随机山脊上叠加若干座主峰：[(峰心 x, 峰高, 峰宽)]。"""
    pts = ridge_points(seed, y_base, amp, rough=rough)
    out = []
    for (x, y) in pts:
        lift = 0.0
        for (cx, ph, pw) in peaks:
            lift += ph * math.exp(-((x - cx) / pw) ** 2)
        out.append((x, max(40.0, y - lift)))
    return out


def paper_base(color: tuple[int, int, int], seed: int) -> Image.Image:
    """生宣肌理：低频云斑 + 细纤维 + 柔光 + 轻微暗角。"""
    img = Image.new("RGB", (W, H), color)
    rng = random.Random(seed)

    # 低频云斑（纸浆厚薄不匀）
    mottle = Image.effect_noise((W // 12, H // 12), 34).resize((W, H), Image.Resampling.BICUBIC)
    mottle = mottle.filter(ImageFilter.GaussianBlur(4))
    dark = mottle.point(lambda v: 255 - int((v / 255.0) ** 1.4 * 9))
    light = mottle.point(lambda v: int((v / 255.0) ** 1.4 * 7))
    rgb = ImageChops.multiply(img, dark.convert("RGB"))
    rgb = ImageChops.screen(rgb, light.convert("RGB"))

    # 纸纤维：极淡短丝，横多竖少
    fib = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fib)
    fiber = (222, 214, 198) if color == PAPER_WARM else (221, 219, 212)
    for _ in range(900):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        ln = rng.uniform(8, 46)
        ang = rng.uniform(-0.35, 0.35) + (0 if rng.random() < 0.72 else math.pi / 2)
        fd.line(
            [(x, y), (x + ln * math.cos(ang), y + ln * math.sin(ang))],
            fill=(*fiber, rng.randint(6, 15)),
            width=1,
        )
    fib = fib.filter(ImageFilter.GaussianBlur(0.4))

    # 漫射柔光：上方略亮，无明确光源
    glow = Image.new("RGBA", (W, H), (253, 250, 241, 255))
    glow.putalpha(vgrad_mask([(0, 0.10), (500, 0.0), (H, 0.0)]))

    out = Image.alpha_composite(rgb.convert("RGBA"), fib)
    out = Image.alpha_composite(out, glow)

    # 暗角（宣纸受光不匀，避免数字感）
    vig = Image.radial_gradient("L").resize((W, H), Image.Resampling.BICUBIC)
    vig = vig.point(lambda v: int(max(0, (v - 130) / 125.0) * 26))
    dark_vig = Image.new("RGBA", (W, H), (92, 82, 62, 255))
    dark_vig.putalpha(vig)
    out = Image.alpha_composite(out, dark_vig)
    return out


def apply_grain(img: Image.Image, strength: float = 1.0) -> Image.Image:
    """哑光颗粒：细微双向噪点，不产生高光。"""
    noise = Image.effect_noise((W, H), 24 * strength).convert("L")
    dark = noise.point(lambda v: 255 - int((255 - v) * 0.085 * strength))
    light = noise.point(lambda v: int(v * 0.055 * strength))
    rgb = img.convert("RGB")
    rgb = ImageChops.multiply(rgb, dark.convert("RGB"))
    rgb = ImageChops.screen(rgb, light.convert("RGB"))
    out = rgb.convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def texture_mask(mask: Image.Image, seed: int, amount: float = 0.10, scale: int = 2) -> Image.Image:
    """给墨块加入纸面细颗粒，避免平涂与块状噪点。"""
    noise = Image.effect_noise((max(16, W // scale), max(16, H // scale)), 68)
    noise = noise.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(0.8))
    factor = noise.point(lambda v: int(255 * (1 - amount + amount * v / 255.0)))
    return ImageChops.multiply(mask, factor)


def mountain(
    pts: list[tuple[int, float]],
    color: tuple[int, int, int],
    alpha: float,
    blur: float,
    vfade: list[tuple[float, float]],
    env_stops: list[tuple[float, float]] | None = None,
    tex: float = 0.10,
    seed: int = 0,
    brush: float = 0.0,
) -> Image.Image:
    """一层山：轮廓 → 迷雾渐隐 → 左右包络 → 纸纹侵蚀 → 柔化 → 皴笔。"""
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.polygon(pts + [(W, H), (0, H)], fill=255)

    mask = ImageChops.multiply(mask, vgrad_mask(vfade))
    if env_stops is not None:
        mask = ImageChops.multiply(mask, hgrad_from(profile(env_stops)))
    if tex > 0:
        mask = texture_mask(mask, seed, tex)
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    mask = mask.point(lambda v: int(v * alpha))
    out = layer(color, mask)

    # 皴法：山体内部短促侧笔，打破平涂
    if brush > 0:
        rng = random.Random(seed * 13 + 7)
        strokes = Image.new("L", (W, H), 0)
        sd = ImageDraw.Draw(strokes)
        for _ in range(int(150 * brush)):
            x, y = rng.uniform(0, W), rng.uniform(0, H)
            ln = rng.uniform(7, 34)
            ang = rng.uniform(1.75, 2.55)
            sd.line(
                [(x, y), (x + ln * math.cos(ang), y + ln * math.sin(ang))],
                fill=rng.randint(35, 130),
                width=rng.choice([1, 1, 2]),
            )
        strokes = strokes.filter(ImageFilter.GaussianBlur(0.7))
        strokes = ImageChops.multiply(strokes, mask)
        shade = tuple(max(0, c - 22) for c in color)
        out = comp(out, layer(shade, strokes))
    return out


def mist_band(
    y_c: float,
    height: float,
    color: tuple[int, int, int],
    alpha: float,
    blur: float,
    env_stops: list[tuple[float, float]] | None = None,
) -> Image.Image:
    """横向雾带：sin² 剖面，边缘零斜率，无缝。"""
    top, bot = y_c - height / 2, y_c + height / 2
    col = []
    for y in range(H):
        if y <= top or y >= bot:
            col.append(0)
        else:
            t = (y - top) / (bot - top)
            col.append(int(255 * alpha * math.sin(math.pi * t) ** 2))
    g = Image.new("L", (1, H))
    g.putdata(col)
    mask = g.resize((W, H), Image.Resampling.NEAREST)
    if env_stops is not None:
        mask = ImageChops.multiply(mask, hgrad_from(profile(env_stops)))
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return layer(color, mask)


def cloud_puff(cx: float, cy: float, rx: float, ry: float, alpha: float, blur: float) -> Image.Image:
    """一团宣纸色云雾。"""
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    for _ in range(7):
        ox, oy = rng_global.uniform(-0.35, 0.35) * rx, rng_global.uniform(-0.45, 0.45) * ry
        d.ellipse(
            [cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry],
            fill=int(200 * alpha),
        )
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return layer(PAPER_WARM, mask)


rng_global = random.Random(77)


def waterfall(x: float, y_top: float, y_bottom: float, width: float, rng: random.Random):
    """飞瀑：两壁夹一水，水口有缺口，落地成雾。返回 (崖壁, 水, 水雾)。"""
    steps = max(2, int(y_bottom - y_top))

    # —— 崖壁：水口两侧的浓墨岩体，上窄下宽 ——
    rock_mask = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(rock_mask)
    for side in (-1, 1):
        prev = None
        for i in range(0, steps, 2):
            y = y_top + i
            t = i / steps
            cx = x + t * width * 0.45
            off = side * (width * (0.55 + 1.15 * t + 0.12 * math.sin(y / 37.0)))
            r = width * (0.42 + 0.55 * t)
            box = [cx + off - r, y - 4, cx + off + r, y + 4]
            rd.ellipse(box, fill=80)
            if prev is not None:
                rd.line([prev, (cx + off, y)], fill=80, width=int(r * 1.4))
            prev = (cx + off, y)
    rock_mask = rock_mask.filter(ImageFilter.GaussianBlur(width * 0.55))
    rock_mask = texture_mask(rock_mask, 91, 0.20, 2)
    rocks = layer((66, 70, 58), rock_mask)

    # —— 水口：瀑顶的暗色缺口，压住水线起点 ——
    notch_mask = Image.new("L", (W, H), 0)
    nd = ImageDraw.Draw(notch_mask)
    nd.ellipse([x - width * 1.1, y_top - width * 0.55, x + width * 1.1, y_top + width * 0.45], fill=150)
    notch_mask = notch_mask.filter(ImageFilter.GaussianBlur(width * 0.5))
    notch = layer((62, 66, 56), notch_mask)

    # —— 水线：主瀑 + 两缕细流，笔直而略带摆荡 ——
    water_mask = Image.new("L", (W, H), 0)
    wd = ImageDraw.Draw(water_mask)
    for strand, (off_f, w_f, a_f) in enumerate([(0.0, 1.0, 255), (-0.55, 0.30, 170), (0.62, 0.35, 185)]):
        for i in range(0, steps, 2):
            y = y_top + i
            t = i / steps
            wobble = math.sin(y / 52.0 + strand) * width * 0.14
            w = width * w_f * (0.30 + 0.60 * t) * (1 - 0.30 * sstep(0.80, 1.0, t))
            cx = x + wobble + t * width * 0.45 + off_f * width * (0.3 + 0.5 * t)
            wd.line([(cx - w / 2, y), (cx + w / 2, y)], fill=a_f, width=2)
    # 飞白：纵纹侵蚀，让水线透气
    streaks = Image.effect_noise((32, max(8, H // 2)), 55).resize((W, H), Image.Resampling.BICUBIC)
    streaks = streaks.point(lambda v: 205 + int(v * 50 / 255)).filter(ImageFilter.GaussianBlur(0.6))
    water_mask = ImageChops.multiply(water_mask, streaks)
    water_mask = water_mask.filter(ImageFilter.GaussianBlur(0.45)).point(lambda v: int(v * 0.88))
    water = layer((250, 248, 240), water_mask)

    # —— 水雾：瀑底与半腰的湿气 ——
    spray_mask = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(spray_mask)
    for _ in range(22):
        rx = width * rng.uniform(1.2, 4.6)
        ry = width * rng.uniform(0.30, 0.95)
        ox = x + rng.uniform(-1, 1) * width * 2.6
        oy = y_bottom - rng.uniform(0, width * 2.2)
        sd.ellipse([ox - rx, oy - ry, ox + rx, oy + ry], fill=rng.randint(55, 120))
    for _ in range(8):
        rx = width * rng.uniform(0.8, 2.0)
        ry = width * rng.uniform(0.2, 0.5)
        ox = x + rng.uniform(-1, 1) * width * 1.2
        oy = y_top + (y_bottom - y_top) * rng.uniform(0.35, 0.75)
        sd.ellipse([ox - rx, oy - ry, ox + rx, oy + ry], fill=rng.randint(25, 55))
    spray_mask = spray_mask.filter(ImageFilter.GaussianBlur(width * 0.9))
    spray = layer((250, 248, 239), spray_mask)

    return rocks, notch, water, spray



def draw_pine(
    d: ImageDraw.ImageDraw,
    x: float,
    y: float,
    h: float,
    rng: random.Random,
    color: tuple[int, int, int, int],
) -> None:
    """远景小松：一竖干、数层短横枝，尺寸小，远看是树不是塔。"""
    lean = rng.uniform(-0.14, 0.10) * h
    trunk = max(1, int(h * 0.070))
    top = (x + lean, y - h)
    d.line([(x, y), top], fill=color, width=trunk)
    # 根部
    d.line([(x, y), (x + rng.uniform(-1.5, 1.5), y - h * 0.18)], fill=color, width=trunk + 1)

    tiers = rng.randint(3, 5)
    for i in range(tiers):
        t = 0.30 + 0.65 * i / (tiers - 1)
        ly = y - h * t
        for side in (-1, 1):
            half = h * (0.16 + 0.30 * t) * rng.uniform(0.75, 1.15)
            d.line([(x + lean * t, ly), (x + lean * t + side * half, ly + h * 0.035)], fill=color, width=1)
            # 枝端两三笔短针
            for k in range(2):
                fx = x + lean * t + side * half * (0.65 + 0.20 * k)
                d.line(
                    [(fx, ly + h * 0.02), (fx + side * h * 0.045, ly - h * 0.045 + k * h * 0.02)],
                    fill=color, width=1,
                )
    # 树顶一点
    d.line([top, (top[0] + rng.uniform(-h * 0.03, h * 0.03), top[1] - h * 0.06)], fill=color, width=1)
    # 树冠：几笔短针收顶
    for k in range(5):
        d.line(
            [(top[0] + rng.uniform(-2, 2), top[1] + k * h * 0.025),
             (top[0] + rng.uniform(-h * 0.07, h * 0.07), top[1] - h * 0.06 + k * h * 0.03)],
            fill=color, width=1,
        )


def pine_grove(
    pts: list[tuple[int, float]],
    x_range: tuple[float, float],
    count_range: tuple[int, int],
    h_range: tuple[float, float],
    rng: random.Random,
    alpha: int = 170,
) -> Image.Image:
    """沿山脊疏密有致地种松。"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    placed: list[float] = []
    target = rng.randint(*count_range)
    candidates = [(px, py) for (px, py) in pts if x_range[0] <= px <= x_range[1]]
    rng.shuffle(candidates)
    for (px, py) in candidates:
        if len(placed) >= target:
            break
        if any(abs(px - q) < 34 for q in placed):
            continue
        placed.append(px)
        h = rng.uniform(*h_range)
        draw_pine(d, px + rng.uniform(-4, 4), py + 5, h, rng, (54, 62, 53, alpha))
    return lay.filter(ImageFilter.GaussianBlur(0.55))


def dot_tree(cx: float, cy: float, h: float, rng: random.Random, color=(64, 98, 66), alpha=170) -> Image.Image:
    """青绿山水里的点叶树：短干 + 团状墨点树冠。"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lean = rng.uniform(-0.18, 0.18) * h
    top = (cx + lean, cy - h * 0.52)
    d.line([(cx, cy), top], fill=(*color, alpha), width=max(1, int(h * 0.055)))
    rx, ry = h * rng.uniform(0.30, 0.42), h * rng.uniform(0.26, 0.36)
    ccx, ccy = top[0], top[1] - ry * 0.25
    # 先铺淡墨树冠，避免点与点之间过空
    d.ellipse(
        [ccx - rx, ccy - ry, ccx + rx, ccy + ry],
        fill=(*color, max(20, int(alpha * 0.18))),
    )
    for _ in range(rng.randint(34, 52)):
        ang = rng.uniform(0, math.tau)
        rr = math.sqrt(rng.random())
        x = ccx + math.cos(ang) * rx * rr
        y = ccy + math.sin(ang) * ry * rr
        r = rng.uniform(1.1, 2.8) * (0.75 + 0.5 * (1 - rr))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, rng.randint(120, 225)))
    return lay.filter(ImageFilter.GaussianBlur(0.7))


def dot_grove(
    centers: list[tuple[float, float, float]],
    rng: random.Random,
) -> Image.Image:
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for (cx, cy, h) in centers:
        lay = Image.alpha_composite(lay, dot_tree(cx, cy, h, rng))
    return lay


def ink_cluster(cx: float, cy: float, count: int, rng: random.Random, color=(60, 74, 58), alpha=(90, 170)) -> Image.Image:
    """石青／石绿点苔与小树簇。"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(count):
        x = cx + rng.uniform(-20, 20)
        y = cy + rng.uniform(-9, 9)
        r = rng.uniform(0.6, 1.9)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, rng.randint(*alpha)))
    return lay.filter(ImageFilter.GaussianBlur(0.6))


def wash_ground(
    y_top: float,
    color: tuple[int, int, int],
    alpha: float,
    env_stops: list[tuple[float, float]],
    blur: float = 10.0,
) -> Image.Image:
    """水面／坡地的大面积淡染，向右或向四周渐隐。"""
    mask = Image.new("L", (W, H), 0)
    vals = []
    for y in range(H):
        vals.append(int(255 * alpha * sstep(y_top - 40, y_top + 260, y)))
    g = Image.new("L", (1, H))
    g.putdata(vals)
    mask = g.resize((W, H), Image.Resampling.NEAREST)
    mask = ImageChops.multiply(mask, hgrad_from(profile(env_stops)))
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return layer(color, mask)


def water_ripples(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    count: int,
    rng: random.Random,
    teal: tuple[int, int, int] = (86, 118, 112),
) -> Image.Image:
    """细微波纹与横向留白。"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(count):
        y0 = rng.uniform(*y_range)
        lam = rng.uniform(220, 620)
        amp = rng.uniform(0.8, 2.2)
        ph = rng.uniform(0, math.tau)
        x1 = rng.uniform(*x_range)
        use_teal = rng.random() < 0.60
        col = (*teal, rng.randint(16, 42)) if use_teal else (250, 247, 238, rng.randint(20, 48))
        pts = [(x, y0 + amp * math.sin(x / lam * math.tau + ph)) for x in range(0, int(x1), 12)]
        d.line(pts, fill=col, width=1, joint="curve")
    return lay.filter(ImageFilter.GaussianBlur(0.9))


# ════════════════════════ 主页：高远山水 ════════════════════════

def generate_home() -> Image.Image:
    rng = random.Random(20261118)
    img = paper_base(PAPER_WARM, 11)

    # —— 远山：淡墨连绵，横贯全幅 ——
    back = ridge_points(101, y_base=470, amp=270, rough=0.88)
    img = comp(img, mountain(
        back, (136, 138, 120), 0.40, 8,
        [(240, 0.85), (430, 0.58), (690, 0.02)],
        tex=0.09, seed=1,
    ))

    # —— 中景：左右两段，中间让出云谷 ——
    mid_l = ridge_points(102, y_base=720, amp=390, rough=0.78)
    img = comp(img, mountain(
        mid_l, (100, 105, 89), 0.56, 3.6,
        [(360, 0.90), (620, 0.55), (860, 0.02)],
        env_stops=[(0, 1.0), (500, 1.0), (850, 0.0), (1920, 0.0)],
        tex=0.14, seed=2, brush=0.9,
    ))
    mid_r = ridge_points(103, y_base=730, amp=370, rough=0.80)
    img = comp(img, mountain(
        mid_r, (97, 102, 87), 0.50, 3.8,
        [(380, 0.88), (640, 0.52), (880, 0.02)],
        env_stops=[(0, 0.0), (1070, 0.0), (1380, 1.0), (1920, 1.0)],
        tex=0.14, seed=3, brush=0.9,
    ))

    # —— 主峰：左巍峨、右呼应，中间留白给入口框 ——
    left = ridge_points(104, y_base=920, amp=560, rough=0.72)
    img = comp(img, mountain(
        left, (49, 53, 44), 0.94, 1.8,
        [(90, 0.98), (740, 0.88), (1060, 0.10)],
        env_stops=[(0, 1.0), (430, 1.0), (800, 0.0), (1920, 0.0)],
        tex=0.20, seed=4, brush=1.5,
    ))
    # 受光面：偏青灰的错位淡层，叠出山体转折
    left_face = ridge_points(105, y_base=940, amp=520, rough=0.76)
    img = comp(img, mountain(
        left_face, (106, 113, 98), 0.24, 2.8,
        [(260, 0.72), (800, 0.42), (1040, 0.02)],
        env_stops=[(0, 0.20), (300, 0.70), (720, 0.0), (1920, 0.0)],
        tex=0.14, seed=5, brush=0.8,
    ))
    right = ridge_points(106, y_base=930, amp=530, rough=0.74)
    img = comp(img, mountain(
        right, (53, 57, 47), 0.90, 1.9,
        [(110, 0.96), (760, 0.86), (1080, 0.08)],
        env_stops=[(0, 0.0), (1130, 0.0), (1440, 1.0), (1920, 1.0)],
        tex=0.20, seed=6, brush=1.4,
    ))
    # 中央远峰：藏在入口框之后，撑起高远
    center = ridge_points(108, y_base=590, amp=420, rough=0.82)
    img = comp(img, mountain(
        center, (124, 128, 112), 0.20, 9,
        [(180, 0.70), (560, 0.30), (800, 0.01)],
        env_stops=[(0, 0.0), (540, 0.30), (960, 1.0), (1380, 0.30), (1920, 0.0)],
        tex=0.08, seed=9,
    ))

    # —— 云海：大团柔雾，不用横条，避免切割画面 ——
    for cx, cy, rx, ry, a in [
        (250, 690, 300, 58, 0.46), (700, 720, 340, 54, 0.50),
        (1180, 700, 330, 56, 0.46), (1680, 725, 300, 52, 0.42),
        (420, 830, 340, 60, 0.40), (980, 860, 400, 62, 0.46),
        (1560, 840, 320, 58, 0.38),
    ]:
        img = comp(img, cloud_puff(cx, cy, rx, ry, a, 40))

    # —— 近崖：左右压角 ——
    cliff_l = ridge_points(107, y_base=1090, amp=300, rough=0.76)
    img = comp(img, mountain(
        cliff_l, (37, 41, 34), 0.96, 1.1,
        [(600, 0.92), (880, 0.48), (1120, 0.03)],
        env_stops=[(0, 1.0), (280, 1.0), (590, 0.0), (1920, 0.0)],
        tex=0.24, seed=7, brush=1.6,
    ))
    cliff_r = ridge_points(109, y_base=1100, amp=280, rough=0.76)
    img = comp(img, mountain(
        cliff_r, (40, 44, 36), 0.94, 1.2,
        [(620, 0.92), (900, 0.44), (1140, 0.02)],
        env_stops=[(0, 0.0), (1340, 0.0), (1600, 1.0), (1920, 1.0)],
        tex=0.24, seed=8, brush=1.5,
    ))

    # —— 崖边植被：以墨点暗示松林，不画具象树形 ——
    for (px, py) in cliff_l:
        if 30 <= px <= 320 and rng.random() < 0.55:
            img = comp(img, ink_cluster(px, py + 3, 22, rng, color=(45, 52, 43), alpha=(55, 120)))
    for (px, py) in cliff_r:
        if 1600 <= px <= 1880 and rng.random() < 0.55:
            img = comp(img, ink_cluster(px, py + 3, 20, rng, color=(48, 55, 45), alpha=(50, 110)))

    # —— 统一调性 ——
    img = Image.blend(img.convert("RGB"), Image.new("RGB", (W, H), PAPER_WARM), 0.02).convert("RGBA")
    img = ImageEnhance.Contrast(img).enhance(1.07)
    img = apply_grain(img, 0.9)
    return img





# ════════════════════════ 旅行：青绿水墨 ════════════════════════

def generate_travel(seed: int = 2026) -> Image.Image:
    rng = random.Random(seed)
    img = paper_base(PAPER_WARM, 21)

    # 右侧留白包络：x>1180 基本为纸
    right_blank = [(0, 1.0), (820, 0.95), (1180, 0.0), (1920, 0.0)]

    # —— 远山：淡墨晕染，朦胧层叠 ——
    far = ridge_points(201, y_base=440, amp=250, rough=0.88)
    img = comp(img, mountain(
        far, (142, 158, 140), 0.44, 6,
        [(230, 0.86), (420, 0.60), (660, 0.02)],
        env_stops=[(0, 1.0), (720, 0.92), (1080, 0.0), (1920, 0.0)],
        tex=0.10, seed=11,
    ))

    # —— 中景：石青薄罩 ——
    mid = ridge_points(202, y_base=680, amp=330, rough=0.82)
    img = comp(img, mountain(
        mid, (80, 127, 115), 0.66, 2.6,
        [(420, 0.94), (660, 0.52), (900, 0.02)],
        env_stops=[(0, 1.0), (520, 0.96), (900, 0.0), (1920, 0.0)],
        tex=0.17, seed=13, brush=1.1,
    ))
    # 石绿：中景偏暖的一层
    mid2 = ridge_points(203, y_base=760, amp=290, rough=0.84)
    img = comp(img, mountain(
        mid2, (106, 142, 99), 0.46, 3.0,
        [(520, 0.88), (760, 0.42), (940, 0.01)],
        env_stops=[(0, 0.95), (420, 0.82), (820, 0.0), (1920, 0.0)],
        tex=0.15, seed=14, brush=0.9,
    ))
    # 近一层青绿主坡
    near = ridge_points(204, y_base=960, amp=330, rough=0.78)
    img = comp(img, mountain(
        near, (48, 82, 71), 0.92, 1.3,
        [(600, 0.92), (830, 0.42), (1030, 0.02)],
        env_stops=[(0, 1.0), (340, 0.96), (740, 0.0), (1920, 0.0)],
        tex=0.21, seed=15, brush=1.5,
    ))

    # —— 云气：大团柔雾，托住山脚 ——
    for cx, cy, rx, ry, a in [
        (250, 720, 300, 48, 0.36), (620, 760, 330, 46, 0.34), (900, 790, 300, 44, 0.28),
    ]:
        img = comp(img, cloud_puff(cx, cy, rx, ry, a, 38))

    # 山间新绿：沿近坡脊线以墨点暗示树丛，悬空处不点
    for (px, py) in near:
        if 40 <= px <= 340 and rng.random() < 0.55:
            img = comp(img, ink_cluster(px, py + 2, 26, rng, color=(66, 104, 64), alpha=(45, 110)))

    # —— 水面：留白处倒映天光 ——
    img = comp(img, wash_ground(870, (148, 183, 175), 0.46, [(0, 1.0), (760, 0.9), (1240, 0.0), (1920, 0.0)], blur=16))
    img = comp(img, water_ripples((0, 1240), (890, 1045), 56, rng))
    # 倒影：近坡在水面的淡影
    refl = ridge_points(205, y_base=1080, amp=260, rough=0.82)
    refl = [(x, 1080 - (1080 - y) * 0.50) for (x, y) in refl]
    img = comp(img, mountain(
        refl, (76, 106, 96), 0.16, 8,
        [(880, 0.55), (1040, 0.18), (1100, 0.01)],
        env_stops=[(0, 0.85), (360, 0.70), (780, 0.0), (1920, 0.0)],
        tex=0.09, seed=16,
    ))

    # —— 近坡：左下角，一株松 + 苔点 ——
    slope = ridge_points(206, y_base=1080, amp=280, rough=0.80)
    img = comp(img, mountain(
        slope, (43, 71, 61), 0.95, 1.0,
        [(740, 0.90), (940, 0.36), (1100, 0.01)],
        env_stops=[(0, 1.0), (260, 0.98), (560, 0.0), (1920, 0.0)],
        tex=0.23, seed=17, brush=1.2,
    ))
    for (px, py) in slope:
        if 40 <= px <= 240 and rng.random() < 0.45:
            img = comp(img, ink_cluster(px, py + 3, 26, rng, color=(40, 62, 52), alpha=(55, 125)))
    img = comp(img, ink_cluster(400, 1035, 28, rng, color=(62, 96, 62), alpha=(80, 170)))

    # —— 统一调性：提青绿、压雾 ——
    img = Image.blend(img.convert("RGB"), Image.new("RGB", (W, H), PAPER_WARM), 0.02).convert("RGBA")
    img = ImageEnhance.Color(img).enhance(1.20)
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = apply_grain(img, 0.9)
    return img





# ════════════════════════ 技能：文人极简 ════════════════════════

def generate_skills() -> Image.Image:
    rng = random.Random(88)
    img = paper_base(PAPER_COOL, 31)

    # —— 隐约笔记横线：极淡，全幅 ——
    lines = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    y = 138.0
    while y < 1010:
        ld.line([(70, y), (W - 70, y)], fill=(74, 72, 62, rng.randint(7, 11)), width=1)
        y += 78 + rng.uniform(-2, 2)
    lines = lines.filter(ImageFilter.GaussianBlur(0.35))
    img = comp(img, lines)

    # —— 最左缘：一道焦墨竖笔 ——
    cx0, y_top, y_bot = 104.0, 74.0, 1014.0
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    walk_l = walk_r = 0.0
    for yy in range(int(y_top), int(y_bot)):
        taper = sstep(y_top, y_top + 90, yy) * (1 - sstep(y_bot - 90, y_bot, yy))
        hw = (30 + 8 * math.sin(yy / 105.0) + 5 * math.sin(yy / 33.0 + 1.3)) * (0.30 + 0.70 * taper)
        cx = cx0 + 6 * math.sin(yy / 150.0) + 2.4 * math.sin(yy / 51.0 + 0.8)
        walk_l = walk_l * 0.95 + rng.uniform(-1.4, 1.4)
        walk_r = walk_r * 0.95 + rng.uniform(-1.4, 1.4)
        md.line([(cx - hw + walk_l, yy), (cx + hw + walk_r, yy)], fill=255, width=1)
    mask = mask.filter(ImageFilter.GaussianBlur(1.0))

    # 飞白：竖向条纹噪声挖空，笔尾渐枯
    def vstripes(h_div: int, sigma: float, seed_add: int) -> Image.Image:
        src = Image.effect_noise((W, max(8, H // h_div)), sigma)
        src = src.point(lambda v, s=seed_add: (v + s) % 256)
        return src.resize((W, H), Image.Resampling.BICUBIC)

    g1 = vstripes(44, 44, 3).point(lambda v: int(max(0.0, min(1.0, (v - 86) / 46.0)) * 255))
    g2 = vstripes(150, 54, 9).point(lambda v: 198 + int(v * 57 / 255))
    gap = ImageChops.multiply(g1, g2).filter(ImageFilter.GaussianBlur(1.2))
    tail = vgrad_mask([(0, 1.0), (640, 0.95), (1014, 0.62)])
    gap = ImageChops.multiply(gap, tail)
    stroke_a = ImageChops.multiply(mask, gap).point(lambda v: int(v * 0.95))

    halo = mask.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.10))
    img = comp(img, layer((36, 36, 32), halo))
    img = comp(img, layer((34, 34, 30), stroke_a))

    # —— 细腻墨点 + 溅点 ——
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for _ in range(16):
        x = rng.uniform(52, 265)
        yv = rng.uniform(110, 990)
        r = rng.uniform(1.2, 4.1)
        dd.ellipse([x - r, yv - r, x + r, yv + r], fill=(30, 30, 27, rng.randint(55, 135)))
    for _ in range(12):
        x = rng.uniform(55, 200)
        yv = rng.uniform(580, 1000)
        r = rng.uniform(0.6, 1.5)
        dd.ellipse([x - r, yv - r, x + r, yv + r], fill=(30, 30, 27, rng.randint(35, 80)))
    img = comp(img, dots.filter(ImageFilter.GaussianBlur(0.45)))

    # —— 飞白枯笔短痕：左侧三分之一，写出节奏 ——
    traces_mask = Image.new("L", (W, H), 0)
    td = ImageDraw.Draw(traces_mask)
    for (tx, ty, ln, ang, wdt) in [
        (rng.uniform(155, 235), rng.uniform(250, 330), rng.uniform(80, 150), rng.uniform(-0.10, 0.05), rng.uniform(4, 7)),
        (rng.uniform(145, 215), rng.uniform(600, 680), rng.uniform(75, 140), rng.uniform(-0.06, 0.10), rng.uniform(3.5, 6)),
        (rng.uniform(175, 255), rng.uniform(850, 930), rng.uniform(70, 125), rng.uniform(-0.08, 0.05), rng.uniform(3, 5.5)),
    ]:
        pts = []
        for i in range(0, int(ln), 5):
            pts.append((tx + i * math.cos(ang), ty + i * math.sin(ang) + math.sin(i / 15.0) * 1.5))
        td.line(pts, fill=255, width=int(wdt))
    traces_mask = traces_mask.filter(ImageFilter.GaussianBlur(0.65))
    dry = Image.effect_noise((W, H), 46).point(lambda v: int(max(0.0, min(1.0, (v - 96) / 74.0)) * 255))
    dry = dry.filter(ImageFilter.GaussianBlur(0.8))
    trace_a = ImageChops.multiply(traces_mask, dry).point(lambda v: int(v * 0.38))
    img = comp(img, layer((48, 48, 43), trace_a))

    # —— 后处理：压高光、哑光颗粒 ——
    img = Image.blend(img.convert("RGB"), Image.new("RGB", (W, H), PAPER_COOL), 0.04).convert("RGBA")
    img = ImageEnhance.Contrast(img).enhance(1.0)
    img = apply_grain(img, 0.85)
    return img


def generate_travel_thumb(path: Path, seed: int, box: tuple[int, int, int, int]) -> None:
    """从旅行山水里裁出 1200x650 的文章缩略图，保持同一画风。"""
    scene = generate_travel(seed).convert("RGB")
    thumb = scene.crop(box)
    thumb = ImageEnhance.Contrast(thumb).enhance(1.12)
    thumb = ImageEnhance.Color(thumb).enhance(1.18)
    thumb.save(path, "JPEG", quality=92, subsampling=0, optimize=True, progressive=True)
    print(f"saved {path}  {thumb.size}  {path.stat().st_size // 1024} KB")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("home-bg.jpg", generate_home),
        ("travel-bg.jpg", generate_travel),
        ("skills-bg.jpg", generate_skills),
    ]
    for name, fn in jobs:
        img = fn().convert("RGB")
        path = OUT_DIR / name
        img.save(path, "JPEG", quality=92, subsampling=0, optimize=True, progressive=True)
        print(f"saved {path}  {img.size}  {path.stat().st_size // 1024} KB")

    (OUT_DIR / "travel").mkdir(parents=True, exist_ok=True)
    for name, seed, box in [
        ("emei.jpg", 2026, (0, 250, 1200, 900)),
        ("taishan.jpg", 3011, (150, 300, 1350, 950)),
        ("leshan.jpg", 4022, (60, 330, 1260, 980)),
    ]:
        generate_travel_thumb(OUT_DIR / "travel" / name, seed, box)


if __name__ == "__main__":
    main()
