import os
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import List


VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif", ".bmp"}


def extract_test_archives(folder: str | Path) -> List[str]:
    """Extract top-level test ZIPs without allowing paths to escape the folder."""
    root = Path(folder).resolve()
    root.mkdir(parents=True, exist_ok=True)
    warnings: List[str] = []

    for archive_path in sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() == ".zip"):
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    relative_path = PurePosixPath(member.filename)
                    if (
                        relative_path.is_absolute()
                        or not relative_path.parts
                        or any(part in {"..", "."} or "\\" in part or ":" in part for part in relative_path.parts)
                    ):
                        warnings.append(f"Caminho ignorado no ZIP {archive_path.name}: {member.filename}")
                        continue

                    destination = (root / Path(*relative_path.parts)).resolve()
                    try:
                        destination.relative_to(root)
                    except ValueError:
                        warnings.append(f"Caminho fora da pasta ignorado no ZIP {archive_path.name}.")
                        continue

                    mode = member.external_attr >> 16
                    if stat.S_ISLNK(mode):
                        warnings.append(f"Link simbólico ignorado no ZIP {archive_path.name}: {member.filename}")
                        continue
                    if member.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                        continue

                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
        except (OSError, zipfile.BadZipFile) as error:
            warnings.append(f"Não foi possível extrair {archive_path.name}: {error}")

    return warnings


def find_test_images(folder: str | Path) -> List[str]:
    image_paths: List[str] = []
    for root, directories, files in os.walk(folder):
        directories[:] = [directory for directory in directories if directory != "__MACOSX"]
        for filename in files:
            if not filename.startswith(".") and Path(filename).suffix.lower() in VALID_IMAGE_EXTENSIONS:
                image_paths.append(os.path.join(root, filename))
    return sorted(image_paths)
