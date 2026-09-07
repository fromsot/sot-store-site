# -*- coding: utf-8 -*-
"""
SOT|店舗Webサポート 店舗サイト生成スクリプト

外部ライブラリは一切使わず、Python標準ライブラリだけで動きます
（npm install や pip install が不要なので、壊れにくく・維持しやすい構成です）。

やること：
  1. data/ フォルダの中にある店舗ごとのJSONファイルを1つずつ読み込む
  2. template/index.html と template/style.css を元に、その店舗用のHTMLを組み立てる
  3. dist/<店舗のslug>/ の中に、そのまま公開できる形で書き出す

使い方：
  python3 build.py

新しい店舗を追加するには：
  1. data/ の中に新しいJSONファイルを1つ追加する（sample-cafe.json を参考にコピーしてよい）
  2. 写真があれば images/<slug>/ に置く
  3. もう一度 python3 build.py を実行する
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "template"
IMAGES_DIR = ROOT / "images"
DIST_DIR = ROOT / "dist"


def load_stores():
    stores = []
    for json_file in sorted(DATA_DIR.glob("*.json")):
        with json_file.open(encoding="utf-8") as f:
            data = json.load(f)
        stores.append(data)
    return stores


def resolve_image(rel_path):
    """images/<slug>/xxx.jpg のような相対パスが実在すればPathを返す。無ければNone。"""
    if not rel_path:
        return None
    candidate = ROOT / rel_path
    return candidate if candidate.is_file() else None


def render_hero_image(store):
    hero_rel = store.get("images", {}).get("hero")
    hero_path = resolve_image(hero_rel)
    if hero_path:
        return '<img src="images/hero{ext}" alt="{name}の外観・内観">'.format(
            ext=hero_path.suffix, name=store.get("name", "")
        )
    return '<div class="photo-placeholder">写真準備中</div>'


def render_gallery_items(store):
    gallery = store.get("images", {}).get("gallery", [])
    if not gallery:
        # データが無い場合は、見た目確認用にプレースホルダーを3枚出す
        return "\n".join(
            '<div class="photo-placeholder">写真準備中</div>' for _ in range(3)
        )
    items = []
    for i, rel_path in enumerate(gallery):
        path = resolve_image(rel_path)
        if path:
            items.append(
                '<img src="images/gallery-{i}{ext}" alt="{name}の写真">'.format(
                    i=i, ext=path.suffix, name=store.get("name", "")
                )
            )
        else:
            items.append('<div class="photo-placeholder">写真準備中</div>')
    return "\n".join(items)


def render_hours_rows(store):
    rows = []
    for entry in store.get("hours", []):
        rows.append(
            "<tr><td class=\"day\">{day}</td><td>{time}</td></tr>".format(
                day=entry.get("day", ""), time=entry.get("time", "")
            )
        )
    return "\n".join(rows)


def render_link_buttons(store):
    links = store.get("links", {})
    buttons = []
    label_map = [
        ("line", "LINEで問い合わせる", "btn"),
        ("reservation", "予約する", "btn accent"),
        ("instagram", "Instagramを見る", "btn accent"),
        ("google_map", "Googleマップで見る", "btn accent"),
    ]
    for key, label, css_class in label_map:
        url = links.get(key)
        if url:
            buttons.append(
                '<a class="{css_class}" href="{url}" target="_blank" rel="noopener">{label}</a>'.format(
                    css_class=css_class, url=url, label=label
                )
            )
    return "\n".join(buttons)


def render_theme_style(store):
    theme = store.get("theme", {})
    if not theme:
        return ""
    lines = []
    if theme.get("primary_color"):
        lines.append("--primary-color: {};".format(theme["primary_color"]))
    if theme.get("background_color"):
        lines.append("--bg-color: {};".format(theme["background_color"]))
    if theme.get("accent_color"):
        lines.append("--accent-color: {};".format(theme["accent_color"]))
    if not lines:
        return ""
    return "<style>:root {{ {rules} }}</style>".format(rules=" ".join(lines))


def build_store(store, template_html, template_css):
    slug = store["slug"]
    out_dir = DIST_DIR / slug
    out_images_dir = out_dir / "images"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    replacements = {
        "##STORE_NAME##": store.get("name", ""),
        "##CATCHCOPY##": store.get("catchcopy", ""),
        "##STORE_DESCRIPTION##": store.get("description", ""),
        "##ADDRESS##": store.get("address", ""),
        "##PHONE##": store.get("phone", ""),
        "##PHONE_TEL##": store.get("phone", "").replace("-", ""),
        "##CLOSED##": store.get("closed", ""),
        "##GOOGLE_MAP_URL##": store.get("links", {}).get("google_map", "#"),
        "##HERO_IMAGE##": render_hero_image(store),
        "##GALLERY_ITEMS##": render_gallery_items(store),
        "##HOURS_ROWS##": render_hours_rows(store),
        "##LINK_BUTTONS##": render_link_buttons(store),
        "##THEME_STYLE##": render_theme_style(store),
    }

    html = template_html
    for key, value in replacements.items():
        html = html.replace(key, value)

    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / "style.css").write_text(template_css, encoding="utf-8")

    # 実在する画像だけコピーする
    hero_path = resolve_image(store.get("images", {}).get("hero"))
    if hero_path:
        out_images_dir.mkdir(exist_ok=True)
        shutil.copy(hero_path, out_images_dir / f"hero{hero_path.suffix}")

    for i, rel_path in enumerate(store.get("images", {}).get("gallery", [])):
        path = resolve_image(rel_path)
        if path:
            out_images_dir.mkdir(exist_ok=True)
            shutil.copy(path, out_images_dir / f"gallery-{i}{path.suffix}")

    return out_dir


def main():
    template_html = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    template_css = (TEMPLATE_DIR / "style.css").read_text(encoding="utf-8")

    stores = load_stores()
    if not stores:
        print("data/ フォルダに店舗データ（.json）が見つかりませんでした。")
        return

    for store in stores:
        out_dir = build_store(store, template_html, template_css)
        print(f"生成しました: {out_dir.relative_to(ROOT)}/index.html")


if __name__ == "__main__":
    main()
