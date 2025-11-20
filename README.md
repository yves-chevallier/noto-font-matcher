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
