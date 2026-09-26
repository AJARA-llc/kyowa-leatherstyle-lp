#!/usr/bin/env python3
"""Build shopify/embed.html: a self-contained HTML+CSS+JS block to paste into a Shopify page.

Source of truth stays index.html. This script:
  - drops the prototype header / drawer / footer (the theme provides those)
  - scopes every CSS rule under .kcs and prefixes ids with kcs- so nothing leaks into other pages
  - rewrites image paths to an absolute base (GitHub Pages by default, or Shopify Files CDN)
  - wires the FINAL CTA to a real /cart/add form (variant ids filled in via KCS_VARIANTS)

Usage: build_embed.py [--base URL] [--product-url PATH]
  --base         where the 26 images live. Default: the GitHub Pages images folder.
                 For Shopify Files use e.g. https://cdn.shopify.com/s/files/1/XXXX/XXXX/files
  --product-url  product page path used by "商品詳細を見る" (default: /products/kawaii-chic-shoulder)
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
OUT = ROOT / "shopify" / "embed.html"

DEFAULT_BASE = "https://ajara-llc.github.io/kyowa-leatherstyle-lp/images"
DROP_SELECTOR_PREFIXES = (".nav", ".drawer", ".icon-btn", ".brand", "footer", "html", "body", "*", "img", "a", "button", "p", "img{")


def scope_css(css: str) -> str:
    """Prefix every selector with .kcs, recursing into @media blocks. Drops header/footer/global rules."""
    out = []
    i = 0
    n = len(css)
    while i < n:
        m = re.compile(r"\s*(/\*.*?\*/)", re.S).match(css, i)
        if m:
            i = m.end()
            continue
        m = re.compile(r"\s*(@[a-z-]+[^{]*)\{", re.S).match(css, i)
        if m:
            depth, j = 1, m.end()
            while j < n and depth:
                depth += (css[j] == "{") - (css[j] == "}")
                j += 1
            inner = scope_css(css[m.end():j - 1])
            if inner.strip():
                out.append(m.group(1).strip() + "{" + inner + "}")
            i = j
            continue
        m = re.compile(r"\s*([^{}]+?)\s*\{([^{}]*)\}", re.S).match(css, i)
        if not m:
            break
        selectors, body = m.group(1), m.group(2)
        i = m.end()
        if selectors.startswith("/*"):
            selectors = re.sub(r"/\*.*?\*/", "", selectors, flags=re.S).strip()
            if not selectors:
                continue
        if selectors.startswith(":root"):
            out.append(".kcs{" + body + "}")
            continue
        parts = [s.strip() for s in selectors.split(",")]
        keep = []
        for sel in parts:
            if not sel or sel.startswith(DROP_SELECTOR_PREFIXES):
                continue
            sel = re.sub(r"#([a-z][\w-]*)", r"#kcs-\1", sel)
            keep.append(".kcs " + sel)
        if keep:
            out.append(", ".join(keep) + "{" + body + "}")
    return "\n".join(out)


def main():
    args = sys.argv[1:]
    base = DEFAULT_BASE
    product_url = "/products/kawaii-chic-shoulder"
    if "--base" in args:
        base = args[args.index("--base") + 1].rstrip("/")
    if "--product-url" in args:
        product_url = args[args.index("--product-url") + 1]

    html = SRC.read_text(encoding="utf-8")
    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    main_html = re.search(r"<main>(.*?)</main>", html, re.S).group(1)
    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)

    # ids -> kcs-ids, and the anchors that point at them
    main_html = re.sub(r'\bid="([a-z][\w-]*)"', r'id="kcs-\1"', main_html)
    main_html = re.sub(r'href="#([a-z][\w-]*)"', r'href="#kcs-\1"', main_html)
    # images -> absolute base, flat filenames (works for both GitHub Pages and Shopify Files)
    main_html = re.sub(r'src="images/([^"]+)"', lambda m: 'src="%s/%s"' % (base, m.group(1)), main_html)
    # FINAL CTA: real cart form instead of the demo button
    main_html = main_html.replace(
        '<button class="btn btn--wide" type="button" id="kcs-addToCartBtn">カートに追加する <span class="ar">→</span></button>',
        '<form action="/cart/add" method="post" id="kcs-cart-form" style="margin:0">'
        '<input type="hidden" name="id" value="" data-kcs-variant>'
        '<input type="hidden" name="quantity" value="1">'
        '<button class="btn btn--wide" type="submit" data-kcs-add>カートに追加する <span class="ar">→</span></button>'
        '</form>')
    main_html = main_html.replace('<a href="#kcs-intro" class="btn btn--line btn--wide">商品詳細を見る</a>',
                                  '<a href="%s" class="btn btn--line btn--wide">商品詳細を見る</a>' % product_url)

    # JS: drop the header/drawer part and the demo alert; scope queries to the wrapper; add the cart wiring
    script = script.split("// カルーセル", 1)[1].split("\n", 1)[1]   # drop the rest of that comment line
    script = script.split("// カートに追加する", 1)[0]
    script = script.replace("document.querySelectorAll", "root.querySelectorAll").replace("document.getElementById('mood-'", "root.querySelector('#kcs-mood-'")
    script = script.replace("var panel = root.querySelector('#kcs-mood-' + tab.getAttribute('data-mood'));", "var panel = root.querySelector('#kcs-mood-' + tab.getAttribute('data-mood'));")

    embed = f"""<!-- Kawaii Chic Shoulder LP — self-contained embed. Paste the whole block into a Shopify page
     (Custom Liquid section or the page HTML editor). Everything is scoped under .kcs; nothing here
     touches other pages. Generated from index.html by scripts/build_embed.py — edit the source, not this file. -->
<div class="kcs" id="kcs-root" translate="no">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');
.kcs{{margin:0;padding:0;font-family:"Inter","Noto Sans JP","Hiragino Kaku Gothic ProN",system-ui,sans-serif;color:#1f1d1b;background:#fff;line-height:1.8;font-weight:400;letter-spacing:.01em;word-break:auto-phrase;line-break:strict;overflow-wrap:break-word;overflow-x:clip;-webkit-font-smoothing:antialiased}}
.kcs *,.kcs *::before,.kcs *::after{{box-sizing:border-box}}
.kcs img{{max-width:100%;display:block;height:auto;border:0;border-radius:0;box-shadow:none}}
.kcs a{{color:inherit;text-decoration:none}}
.kcs button{{font-family:inherit;font-size:inherit;color:inherit;min-height:0;min-width:0;box-shadow:none;text-transform:none;letter-spacing:normal}}
.kcs p,.kcs h1,.kcs h2,.kcs h3,.kcs ul{{margin:0;padding:0;color:inherit;font-family:inherit;letter-spacing:normal;text-transform:none;text-shadow:none}}
.kcs ul{{list-style:none}}
.kcs form{{margin:0}}
{scope_css(css)}
</style>
{main_html.strip()}
<script>
(function(){{
  var root = document.getElementById('kcs-root');
  if(!root) return;
{script.strip()}

  // カート追加: 色名 -> バリアントID。Shopify管理画面の「商品 > バリエーション」の各IDをここに入れる。
  // 空のままなら「商品詳細を見る」と同じ商品ページへ移動する。
  var KCS_VARIANTS = {{
    // "PINK BEIGE": 12345678901234,
  }};
  var KCS_PRODUCT_URL = "{product_url}";
  var form = root.querySelector('#kcs-cart-form');
  if(form){{
    var idInput = form.querySelector('[data-kcs-variant]');
    var first = Object.keys(KCS_VARIANTS)[0];
    if(first) idInput.value = KCS_VARIANTS[first];
    form.addEventListener('submit', function(e){{
      if(!idInput.value){{ e.preventDefault(); location.href = KCS_PRODUCT_URL; }}
    }});
  }}
}})();
</script>
</div>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(embed, encoding="utf-8")
    print("wrote %s (%d chars, %d KB)" % (OUT.relative_to(ROOT), len(embed), len(embed.encode()) // 1024))


if __name__ == "__main__":
    main()
