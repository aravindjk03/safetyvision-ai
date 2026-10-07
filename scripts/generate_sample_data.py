"""
SafetyVision AI — Synthetic Industrial Dataset & Acceptance Test Case Generator
Creates realistic synthetic industrial images with ground-truth bounding box labels
for training, validation, and automated acceptance testing.
"""

from pathlib import Path
import random
from typing import Dict, List, Tuple
import cv2
import numpy as np

# Class mapping
CLASS_MAP = {
    "grinder": 0,
    "guard": 1,
    "handle": 2,
    "cable": 3,
    "switch": 4,
    "damaged_guard": 5,
    "damaged_cable": 6,
    "person": 7,
}

TOOL_COLORS = [
    (180, 90, 0),     # Bosch blue-teal
    (0, 180, 220),    # DeWalt yellow
    (140, 140, 0),    # Makita teal
    (20, 20, 180),    # Milwaukee red
    (40, 100, 30),    # Metabo dark green
    (0, 110, 230),    # Black & Decker orange
    (50, 50, 55),     # Matte industrial charcoal
]


def draw_textured_grinder(
    width: int = 640,
    height: int = 640,
    include_guard: bool = True,
    include_handle: bool = True,
    include_cable: bool = True,
    include_switch: bool = True,
    damage_guard: bool = False,
    damage_cable: bool = False,
    include_person: bool = False,
    offset_x: int = 0,
    offset_y: int = 0,
    tool_color: Tuple[int, int, int] = (180, 90, 0),
    blur_level: int = 0,
    darken: bool = False,
    flip_h: bool = False,
    bg_style: str = "steel",
) -> Tuple[np.ndarray, List[Tuple[int, float, float, float, float]]]:
    """
    Renders an industrial angle grinder scene with ground truth YOLO bounding boxes.
    Supports left/right orientations, multiple industrial table textures, and defect varieties.
    """
    # 1. Background Generation
    if bg_style == "concrete":
        bg_base = [90, 90, 95]
    elif bg_style == "wood":
        bg_base = [60, 75, 95]  # Oily workshop wood
    elif bg_style == "rubber":
        bg_base = [38, 42, 45]  # Anti-static mat
    elif bg_style == "cast_iron":
        bg_base = [50, 52, 55]
    else:  # steel
        bg_base = [75, 80, 85]

    bg = np.zeros((height, width, 3), dtype=np.uint8)
    bg[:, :] = bg_base
    noise = np.random.normal(0, 15, bg.shape).astype(np.int16)
    bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Industrial scratch textures or diamond grid lines
    if random.random() < 0.5:
        for _ in range(random.randint(4, 10)):
            sx = random.randint(0, width)
            sy = random.randint(0, height)
            ex = sx + random.randint(-200, 200)
            ey = sy + random.randint(-90, 90)
            cv2.line(bg, (sx, sy), (ex, ey), (115, 115, 120), 1)

    labels = []

    def to_yolo(x1, y1, x2, y2, cid):
        cx = (x1 + x2) / 2.0 / width
        cy = (y1 + y2) / 2.0 / height
        w = (x2 - x1) / width
        h = (y2 - y1) / height
        return (cid, round(cx, 6), round(cy, 6), round(w, 6), round(h, 6))

    # Base grinder position in center + offsets
    gx1, gy1 = 180 + offset_x, 240 + offset_y
    gx2, gy2 = 460 + offset_x, 380 + offset_y

    # Clamp coordinates inside frame
    gx1 = max(110, min(width - 330, gx1))
    gy1 = max(120, min(height - 210, gy1))
    gx2 = gx1 + 280
    gy2 = gy1 + 140

    # Draw cast shadow under equipment
    shadow_pts = np.array([
        [gx1 - 30, gy2 + 10],
        [gx2 + 80, gy2 + 15],
        [gx2 + 60, gy2 + 35],
        [gx1 - 50, gy2 + 25]
    ], np.int32)
    cv2.fillPoly(bg, [shadow_pts], (20, 20, 20))

    # Draw person in background if requested
    if include_person:
        px1 = max(10, min(width - 160, 30 + offset_x // 2))
        py1 = max(10, min(height - 320, 20 + offset_y // 2))
        px2, py2 = px1 + 130, py1 + 280
        cv2.rectangle(bg, (px1, py1), (px2, py2), (120, 110, 100), -1)
        cv2.circle(bg, (int((px1 + px2) / 2), py1 + 35), 28, (160, 140, 130), -1)
        labels.append(to_yolo(px1, py1, px2, py2, CLASS_MAP["person"]))

    # Draw Cable (attached to rear: left side of grinder body)
    if include_cable:
        cx1, cy1 = gx1 - 110, gy1 + 50
        cx2, cy2 = gx1 + 15, gy1 + 90
        cable_color = (25, 25, 25)  # Matte black rubber
        cv2.rectangle(bg, (cx1, cy1), (cx2, cy2), cable_color, -1)
        # Anti-kink sleeve
        cv2.rectangle(bg, (gx1 - 20, cy1 - 5), (gx1 + 15, cy2 + 5), (50, 50, 50), -1)

        if damage_cable:
            # Draw fraying / exposed copper sparks & colored wire insulation
            cv2.rectangle(bg, (cx1 + 30, cy1 + 3), (cx1 + 75, cy2 - 3), (0, 140, 255), -1)
            cv2.line(bg, (cx1 + 35, cy1 + 2), (cx1 + 70, cy2 + 8), (220, 50, 0), 2)
            cv2.line(bg, (cx1 + 45, cy1 - 2), (cx1 + 65, cy2 + 2), (0, 230, 255), 2)
            labels.append(to_yolo(cx1, cy1, cx2, cy2, CLASS_MAP["damaged_cable"]))
        else:
            labels.append(to_yolo(cx1, cy1, cx2, cy2, CLASS_MAP["cable"]))

    # Draw Main Grinder Motor Body
    cv2.rectangle(bg, (gx1, gy1), (gx2, gy2), tool_color, -1)
    # Metal gearbox front
    gear_x1 = gx2 - 80
    gear_x2 = gx2 + 25
    cv2.rectangle(bg, (gear_x1, gy1 - 10), (gear_x2, gy2 + 10), (145, 150, 155), -1)
    # Ventilation slits
    for vx in range(gx1 + 30, gear_x1 - 20, 20):
        cv2.line(bg, (vx, gy1 + 20), (vx, gy2 - 20), (30, 30, 30), 3)

    labels.append(to_yolo(gx1, gy1 - 10, gear_x2, gy2 + 10, CLASS_MAP["grinder"]))

    # Draw Safety Switch on body
    if include_switch:
        sx1, sy1 = gx1 + 70, gy1 - 10
        sx2, sy2 = gx1 + 125, gy1 + 12
        cv2.rectangle(bg, (sx1, sy1), (sx2, sy2), (30, 30, 200), -1)  # Red paddle switch
        labels.append(to_yolo(sx1, sy1, sx2, sy2, CLASS_MAP["switch"]))

    # Draw Auxiliary Side Handle (screwed into gear head)
    if include_handle:
        hx1, hy1 = gear_x1 + 10, gy1 - 120
        hx2, hy2 = gear_x1 + 70, gy1
        cv2.rectangle(bg, (hx1, hy1), (hx2, hy2), (25, 25, 25), -1)
        for ry in range(hy1 + 10, hy2 - 20, 15):
            cv2.line(bg, (hx1, ry), (hx2, ry), (65, 65, 65), 2)
        labels.append(to_yolo(hx1, hy1, hx2, hy2, CLASS_MAP["handle"]))

    # Draw Wheel Guard (curved semicircular metal cover around spindle)
    if include_guard:
        gdx1, gdy1 = gear_x1 + 40, gy1 - 25
        gdx2, gdy2 = gear_x1 + 165, gy2 + 25
        guard_color = (60, 60, 60) if not damage_guard else (45, 45, 45)
        center_spindle = (int((gdx1 + gdx2) / 2), int((gdy1 + gdy2) / 2))
        cv2.ellipse(bg, center_spindle, (58, 72), 0, 180, 360, guard_color, -1)
        cv2.ellipse(bg, center_spindle, (58, 72), 0, 180, 360, (205, 205, 205), 4)

        if damage_guard:
            # Draw visible jagged fracture line and structural bend
            cv2.line(bg, (gdx1 + 15, gdy1 + 20), (gdx2 - 15, gdy2 - 15), (0, 0, 230), 4)
            cv2.line(bg, (gdx1 + 35, gdy1 + 10), (gdx1 + 65, gdy2 - 10), (255, 255, 255), 2)
            labels.append(to_yolo(gdx1, gdy1, gdx2, gdy2, CLASS_MAP["damaged_guard"]))
        else:
            labels.append(to_yolo(gdx1, gdy1, gdx2, gdy2, CLASS_MAP["guard"]))

    # Horizontal Mirroring / Left-handed orientation
    if flip_h:
        bg = cv2.flip(bg, 1)
        flipped_labels = []
        for cid, cx, cy, w, h in labels:
            flipped_labels.append((cid, round(1.0 - cx, 6), cy, w, h))
        labels = flipped_labels

    # Postprocessing variations (Blur, Darken)
    if blur_level > 0:
        bg = cv2.GaussianBlur(bg, (blur_level * 2 + 1, blur_level * 2 + 1), 0)

    if darken:
        bg = (bg.astype(np.float32) * 0.35).astype(np.uint8)

    return bg, labels


def generate_all_sample_datasets(root_dir: Path) -> Dict[str, int]:
    """Generates comprehensive industrial training, validation, and acceptance test sets."""
    dataset_dir = root_dir / "dataset"
    counts = {"train": 0, "val": 0, "test": 0}

    # Scaled splits: 600 train, 120 val, 80 test = 800 images total
    splits = [
        ("train", 600),
        ("val", 120),
        ("test", 80),
    ]

    bg_styles = ["steel", "concrete", "wood", "rubber", "cast_iron"]

    for split, count in splits:
        img_dir = dataset_dir / "images" / split
        lbl_dir = dataset_dir / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for i in range(count):
            has_guard = random.random() > 0.14
            # 22% of guards are damaged, giving ~180 damaged guard instances across dataset
            damage_guard = has_guard and (random.random() < 0.22)
            has_handle = random.random() > 0.15
            has_cable = random.random() > 0.10
            # 18% of cables are damaged, giving ~150 damaged cable instances across dataset
            damage_cable = has_cable and (random.random() < 0.18)
            has_switch = random.random() > 0.10
            has_person = random.random() < 0.32

            off_x = random.randint(-65, 65)
            off_y = random.randint(-50, 50)
            t_col = random.choice(TOOL_COLORS)
            bg_style = random.choice(bg_styles)
            flip = random.random() < 0.35  # 35% flipped/mirrored orientations

            blur = random.choice([0, 0, 0, 1, 2]) if random.random() < 0.20 else 0
            dark = random.random() < 0.08

            img, labels = draw_textured_grinder(
                include_guard=has_guard,
                include_handle=has_handle,
                include_cable=has_cable,
                include_switch=has_switch,
                damage_guard=damage_guard,
                damage_cable=damage_cable,
                include_person=has_person,
                offset_x=off_x,
                offset_y=off_y,
                tool_color=t_col,
                blur_level=blur,
                darken=dark,
                flip_h=flip,
                bg_style=bg_style,
            )

            filename = f"sample_{split}_{i:03d}"
            img_path = img_dir / f"{filename}.jpg"
            lbl_path = lbl_dir / f"{filename}.txt"

            cv2.imwrite(str(img_path), img)
            with open(lbl_path, "w", encoding="utf-8") as f:
                for lbl in labels:
                    f.write(f"{lbl[0]} {lbl[1]} {lbl[2]} {lbl[3]} {lbl[4]}\n")

            counts[split] += 1

    # Specifically generate the 5 Acceptance Test Cases into test folder
    test_img_dir = dataset_dir / "images" / "test"
    test_lbl_dir = dataset_dir / "labels" / "test"

    acceptance_cases = [
        ("acceptance_01_pass_full.jpg", dict(include_guard=True, include_handle=True, include_cable=True, include_switch=True)),
        ("acceptance_02_fail_missing_guard.jpg", dict(include_guard=False, include_handle=True, include_cable=True, include_switch=True)),
        ("acceptance_03_fail_damaged_guard.jpg", dict(include_guard=True, damage_guard=True, include_handle=True, include_cable=True, include_switch=True)),
        ("acceptance_04_fail_damaged_cable.jpg", dict(include_guard=True, include_handle=True, include_cable=True, damage_cable=True, include_switch=True)),
        ("acceptance_05_review_dark_blur.jpg", dict(include_guard=True, include_handle=True, include_cable=True, include_switch=True, blur_level=4, darken=True)),
    ]

    for fname, kwargs in acceptance_cases:
        img, labels = draw_textured_grinder(**kwargs)
        base = fname.replace(".jpg", "")
        cv2.imwrite(str(test_img_dir / fname), img)
        with open(test_lbl_dir / f"{base}.txt", "w", encoding="utf-8") as f:
            for lbl in labels:
                f.write(f"{lbl[0]} {lbl[1]} {lbl[2]} {lbl[3]} {lbl[4]}\n")
        counts["test"] += 1

    return counts


if __name__ == "__main__":
    current = Path(__file__).resolve().parent.parent
    result = generate_all_sample_datasets(current)
    print(f"Generated comprehensive industrial dataset: {result}")

