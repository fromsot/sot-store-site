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

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "template"
IMAGES_DIR = ROOT / "images"
DIST_DIR = ROOT / "dist"

# 店舗JSONの色指定として許可する形式（#fff / #ffffff のみ）。
# これ以外の値が来た場合はテーマ色を適用せず、テンプレート標準の色にフォールバックする
# （<style>タグの中にそのまま差し込む値なので、想定外の文字列を許可しないための安全対策）。
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$")


def esc(value):
    """店舗データ（店名・住所など）をHTMLに埋め込む前に必ずエスケープする。

    店名に「&」「<」「"」などが含まれるとページが壊れる／表示が崩れるバグが
    あったため追加。以後、店舗データをテンプレートに差し込む箇所は必ずこれを通す。
    """
    return html.escape(str(value or ""), quote=True)


def safe_color(value):
    """テーマ色として安全な値（#fffまたは#ffffff形式）だけを通す。"""
    if value and COLOR_PATTERN.match(value):
        return value
    return None


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


# 写真未準備のヒーロー枠に表示する、カメラのアイコン（SVG）。
# 特定サービスのロゴではなく汎用アイコンなので、著作権・商標の心配なく使える。
CAMERA_ICON_SVG = (
    '<svg viewBox="0 0 24 24" width="32" height="32" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Z"/>'
    '<circle cx="12" cy="13" r="3.5"/>'
    "</svg>"
)

# ボタン群で使うアイコン（すべて汎用アイコン。LINE/Instagram公式ロゴそのものではない）。
BUTTON_ICONS = {
    "line": (
        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M4 12a8 5.5 0 1 1 3 4.3L4 20l1-4A5.3 5.3 0 0 1 4 12Z"/>'
        "</svg>"
    ),
    "reservation": (
        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<rect x="4" y="5" width="16" height="15" rx="2"/>'
        '<path d="M4 10h16M8 3v4M16 3v4"/>'
        "</svg>"
    ),
    "instagram": (
        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<rect x="3.5" y="3.5" width="17" height="17" rx="4.5"/>'
        '<circle cx="12" cy="12" r="4"/>'
        '<circle cx="17" cy="7" r="0.9" fill="currentColor" stroke="none"/>'
        "</svg>"
    ),
    "google_map": (
        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 21s7-6.3 7-11.5A7 7 0 0 0 5 9.5C5 14.7 12 21 12 21Z"/>'
        '<circle cx="12" cy="9.5" r="2.3"/>'
        "</svg>"
    ),
}


def render_hero_image(store):
    hero_rel = store.get("images", {}).get("hero")
    hero_path = resolve_image(hero_rel)
    if hero_path:
        return '<img src="images/hero{ext}" alt="{name}の外観・内観">'.format(
            ext=hero_path.suffix, name=esc(store.get("name", ""))
        )
    return (
        '<div class="photo-placeholder hero-placeholder">'
        + CAMERA_ICON_SVG
        + "<span>写真準備中</span></div>"
    )


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
                    i=i, ext=path.suffix, name=esc(store.get("name", ""))
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
                day=esc(entry.get("day", "")), time=esc(entry.get("time", ""))
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
            icon = BUTTON_ICONS.get(key, "")
            buttons.append(
                '<a class="{css_class}" href="{url}" target="_blank" rel="noopener">'
                '{icon}<span>{label}</span></a>'.format(
                    css_class=css_class, url=esc(url), icon=icon, label=esc(label)
                )
            )
    return "\n".join(buttons)


def render_theme_style(store):
    theme = store.get("theme", {})
    if not theme:
        return ""
    lines = []
    primary = safe_color(theme.get("primary_color"))
    bg = safe_color(theme.get("background_color"))
    accent = safe_color(theme.get("accent_color"))
    if primary:
        lines.append("--primary-color: {};".format(primary))
    if bg:
        lines.append("--bg-color: {};".format(bg))
    if accent:
        lines.append("--accent-color: {};".format(accent))
    if not lines:
        return ""
    return "<style>:root {{ {rules} }}</style>".format(rules=" ".join(lines))


def render_og_image_tag(store):
    """OGP画像タグ。ヒーロー写真がある店舗だけ出力する（無い店舗は何も出さない）。"""
    hero_path = resolve_image(store.get("images", {}).get("hero"))
    if not hero_path:
        return ""
    return '<meta property="og:image" content="images/hero{ext}">'.format(
        ext=hero_path.suffix
    )


def build_store(store, template_html, template_css):
    slug = store["slug"]
    out_dir = DIST_DIR / slug
    out_images_dir = out_dir / "images"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    replacements = {
        "##STORE_NAME##": esc(store.get("name", "")),
        "##CATCHCOPY##": esc(store.get("catchcopy", "")),
        "##STORE_DESCRIPTION##": esc(store.get("description", "")),
        "##ADDRESS##": esc(store.get("address", "")),
        "##PHONE##": esc(store.get("phone", "")),
        "##PHONE_TEL##": esc(store.get("phone", "").replace("-", "")),
        "##CLOSED##": esc(store.get("closed", "")),
        "##GOOGLE_MAP_URL##": esc(store.get("links", {}).get("google_map", "#")),
        "##HERO_IMAGE##": render_hero_image(store),
        "##GALLERY_ITEMS##": render_gallery_items(store),
        "##HOURS_ROWS##": render_hours_rows(store),
        "##LINK_BUTTONS##": render_link_buttons(store),
        "##THEME_STYLE##": render_theme_style(store),
        "##OG_IMAGE_TAG##": render_og_image_tag(store),
    }

    page_html = template_html
    for key, value in replacements.items():
        page_html = page_html.replace(key, value)

    (out_dir / "index.html").write_text(page_html, encoding="utf-8")
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
