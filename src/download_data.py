"""Download the original UCI Online Retail workbook without generating data."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
SOURCE_URL = "https://archive.ics.uci.edu/dataset/352/online%2Bretail"
FILENAME = "Online Retail.xlsx"


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download_data(output_dir: str | Path = ROOT / "data/raw", force: bool = False) -> Path:
    """Keep the official workbook intact and record reproducible provenance."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / FILENAME
    metadata_path = output_dir / "SOURCE.json"
    if target.exists() and metadata_path.exists() and not force:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if sha256_file(target) != metadata["sha256"]:
            raise ValueError("原始Excel校验失败。请确认文件未被修改，或使用 --force 重新下载。")
        return target

    request = Request(DOWNLOAD_URL, headers={"User-Agent": "OnlineRetailCourseProject/1.0"})
    with urlopen(request, timeout=120) as response:
        payload = response.read()
        resolved_url = response.url
    with ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if Path(name).name == FILENAME]
        if len(names) != 1:
            raise ValueError(f"官方压缩包中未找到唯一的 {FILENAME}")
        # Read the known workbook only; do not extract arbitrary archive paths.
        workbook = archive.read(names[0])
    temporary = target.with_suffix(".xlsx.part")
    temporary.write_bytes(workbook)
    temporary.replace(target)
    metadata = {
        "dataset": "Online Retail",
        "creator": "Daqing Chen",
        "repository": "UCI Machine Learning Repository",
        "source_url": SOURCE_URL,
        "download_url": DOWNLOAD_URL,
        "resolved_download_url": resolved_url,
        "doi": "10.24432/C5BW33",
        "citation": "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33.",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "filename": FILENAME,
        "size_bytes": target.stat().st_size,
        "sha256": sha256_file(target),
        "archive_sha256": hashlib.sha256(payload).hexdigest(),
        "expected_rows_from_source": 541909,
        "period_from_source": "2010-12-01 to 2011-12-09",
        "modifications": "None to original workbook. Cleaning and derived warehouse tables are implemented separately.",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="下载UCI真实零售原始数据")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(download_data(args.output_dir, args.force))
