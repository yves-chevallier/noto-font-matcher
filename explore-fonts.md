L'idée est de télécharger l'ensemble des polices TTF sur: https://notofonts.github.io/ par scapping links comme https://cdn.jsdelivr.net/gh/notofonts/notofonts.github.io/fonts/NotoSansAdlam/unhinted/ttf/NotoSansAdlam-Bold.ttf

On pourrait utiliser ttfdump ou alors un outil python. L'idée est:

1. Télécharger toutes les polices Noto les mettre dans un dossier fonts/
2. Pour chaque police, construire une db (yaml?) avec le nom du ttf, les ranges unicode couverts

Écrit moi un script python ou bash pour faire ça.

## Script prêt à l'emploi

Le fichier `fetch_noto_fonts.py` fait tout :
- Scrap la page https://notofonts.github.io pour récupérer tous les liens TTF (jsDelivr)
- Télécharge chaque TTF dans `fonts/<family>/`
- Lit les cmaps avec fontTools et écrit `fonts.yaml` avec `family`, `file`, `unicode_ranges`

Pré-requis :
```bash
pip install requests pyyaml fonttools
```

Exécution :
```bash
python fetch_noto_fonts.py
```

Option utile pour tester sans tout télécharger (6k+ fichiers) :
```bash
python fetch_noto_fonts.py --limit 10
```
