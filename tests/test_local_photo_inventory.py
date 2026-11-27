import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_candidate_batch.py"
SPEC = importlib.util.spec_from_file_location("candidate_batch_local_inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LocalPhotoInventoryTests(unittest.TestCase):
    def test_inventory_keeps_local_images_unapproved_and_reads_manifest_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            collection = base / "almendras-fotos-propias-revision-1" / "nuevas_aportaciones"
            original = collection / "originales"
            optimized = collection / "optimizadas_webp"
            original.mkdir(parents=True)
            optimized.mkdir(parents=True)
            # A tiny valid PNG is enough to exercise the metadata inventory.
            from PIL import Image
            Image.new("RGB", (32, 24), "white").save(original / "aportacion-01.png")
            (collection / "manifest.json").write_text(json.dumps({
                "fotografias": [{
                    "numero": 1,
                    "archivo_original": "nuevas_aportaciones/originales/aportacion-01.png",
                    "identificacion": "Pendiente de confirmar",
                    "estado": "Recibida; no asignada"
                }]
            }), encoding="utf-8")
            with patch.object(MODULE, "ROOT", base / "repo"):
                (base / "repo" / "docs").mkdir(parents=True)
                result = MODULE.index_local_photo_candidates(base)
            self.assertEqual(result, 0)
            data = json.loads((base / "repo" / "docs" / "local_photo_inventory.json").read_text())
            self.assertEqual(data["total_files"], 1)
            record = data["records"][0]
            self.assertEqual(record["approval_status"], "PENDING_VISUAL_VARIANT_AND_RIGHTS_REVIEW")
            self.assertEqual(record["contribution_number"], 1)
            self.assertIsNone(record["suggested_product"])
            self.assertEqual(record["width"], 32)


if __name__ == "__main__":
    unittest.main()
