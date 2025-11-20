# Font

fc-match -f "%{family}\n" "🍕"
fc-match -f "%{family}\n" "ܛ"

fc-match "sans:lang=ja"

fc-query --charsets /usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf

sudo apt install harfbuzz-tools
hb-view /usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf "ខ្មែរ"
for f in /usr/share/fonts/**/*.ttf; do
    hb-view "$f" "𗍥" >/dev/null 2>&1 && echo "$f"
done

## History

A l'origine (1980-1982) Donald Knuth a créé METAFONT pour concevoir des polices de caractères
vectorielles destinées à être utilisées avec son système de composition de texte TeX.

Il a créé Computer Modern (CM) comme police par défaut pour TeX. CM est une famille bitmap + METAFONT.
Seulement Roman, Sans, Typewriter + variations math rudimentaires.

CM-Super est arrivé plus tard pour fournir des polices vectorielles PostScript basées sur CM.
CM-Super, EC Type1, LH Type1 (russe).

Pour remplacer CM-Super, Latin Modern (LM) a été développé en 2003+. Certaines métriques ont légèrement été corrigées des courbes plus propres, plus de glyphes et des versions OTF.

Ensuite pour Unicode COmputer Modern Unicode CMU apporte la prise en charge Unicode, parfaite pour XeLaTeX et LuaLaTeX

## OTF vs TTF

For \LaTeX, OTF is generally preferred over TTF due to better support for advanced typographic features and superior rendering quality. OTF fonts often include additional features like ligatures, alternate characters, and improved kerning, which enhance the overall appearance of the text. Additionally, OTF fonts are more compatible with LaTeX's font handling system, making them a better choice for professional typesetting.

## Real alternatives

- CMU (Computer Modern Unicode)
- CMU Sans serif
- Libertinus (Libertinus Serif, Libertinus Sans, Libertinus Mono)
- TeX Gyre Pagella
- STIX Two

Use Noto for the fallback unicode (Emoji, CJK, etc.)
