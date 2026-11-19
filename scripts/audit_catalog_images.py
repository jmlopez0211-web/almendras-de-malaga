#!/usr/bin/env python3
"""Source-level audit of catalog photo references; never approves images."""
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'data/catalog.js').read_text(encoding='utf-8')
blocks=re.findall(r'"([^"\\]+)":\s*\{(.*?)\n\s*\}',text,re.S)
rows=[]
for key,block in blocks:
 def field(name):
  m=re.search(r'"'+re.escape(name)+r'"\s*:\s*"((?:\\.|[^"\\])*)"',block)
  return m.group(1) if m else None
 image=field('image'); verified=re.search(r'"imageVerified"\s*:\s*(true|false)',block)
 rows.append({'key':key,'name':field('name') or key,'image':image,'imageVerified':(verified.group(1)=='true') if verified else None,'missing_image':not image,'missing_source':bool(image) and not field('imageSource'),'missing_credit':bool(image) and not field('imageCredit'),'missing_license':bool(image) and not field('imageLicense'),'local_file_missing':bool(image) and not image.startswith(('http://','https://')) and not (ROOT/image).is_file()})
summary={'catalog_products_detected':len(rows),'missing_image':sum(r['missing_image'] for r in rows),'verified_true':sum(r['imageVerified'] is True for r in rows),'verified_false':sum(r['imageVerified'] is False for r in rows),'verification_unspecified':sum(r['imageVerified'] is None for r in rows),'missing_source':sum(r['missing_source'] for r in rows),'missing_credit':sum(r['missing_credit'] for r in rows),'missing_license':sum(r['missing_license'] for r in rows),'local_file_missing':sum(r['local_file_missing'] for r in rows)}
report={'summary':summary,'products':rows}
(ROOT/'docs/photo-catalog-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# Auditoría automática de referencias fotográficas','','**Limitación:** análisis de código/metadatos; no inspecciona visualmente archivos ni valida licencias.','## Resumen']+[f'- **{k}:** {v}' for k,v in summary.items()]+['','## Productos sin imagen']+[f'- {r["key"]} — {r["name"]}' for r in rows if r['missing_image']]+['','## Imágenes no verificadas']+[f'- {r["key"]} — {r["name"]} (imageVerified={r["imageVerified"]})' for r in rows if r['imageVerified'] is not True]+['','## Referencias locales inexistentes']+[f'- {r["key"]} — {r["image"]}' for r in rows if r['local_file_missing']]+['','## Metadatos incompletos']+[f'- {r["key"]} — fuente:{r["missing_source"]}; crédito:{r["missing_credit"]}; licencia:{r["missing_license"]}' for r in rows if r['missing_source'] or r['missing_credit'] or r['missing_license']]
(ROOT/'docs/photo-catalog-audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
