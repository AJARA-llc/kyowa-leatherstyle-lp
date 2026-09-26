# Embedding the LP in a Shopify page

`embed.html` is a single self-contained block (HTML + CSS + JS). Everything is scoped
under the `.kcs` wrapper, ids are prefixed `kcs-`, so it cannot affect other pages or
the theme. The theme's own header and footer wrap it.

## Steps (Dawn or any OS 2.0 theme)

1. **Create the page** — Online Store > Pages > Add page. Title "Kawaii Chic Shoulder".
   Leave the content empty and save.
2. **Give it a blank template** — Online Store > Themes > Customize > open the page
   > "Create template" (e.g. `kawaii-chic`). Remove the default *Page* section so the
   title does not show, then **Add section > Custom Liquid**.
3. **Paste** the whole contents of `embed.html` into the Custom Liquid box and save.
   (The block is under the 50,000-character limit of that setting.)
4. **Images** load from GitHub Pages by default. To serve them from Shopify instead,
   upload `../images/*.jpg` in Content > Files, then rebuild with your Files base URL:
   `python3 scripts/build_embed.py --base https://cdn.shopify.com/s/files/1/XXXX/XXXX/files`
   and paste again.
5. **Cart button** — in the `KCS_VARIANTS` map at the bottom of the block, enter the
   variant id for each colour (Products > the product > Variants > the id in the URL).
   Until ids are entered the button sends the visitor to the product page given by
   `--product-url` (default `/products/kawaii-chic-shoulder`).

Rebuild after any change to `index.html`: `python3 scripts/build_embed.py`.
