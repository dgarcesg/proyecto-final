"""Publica la app en Hugging Face Spaces.

Necesita en .env (que nunca se sube a GitHub):
    HF_TOKEN=...            token de Hugging Face con permiso de escritura ("Write")
    ANTHROPIC_API_KEY=...   se guarda en el Space como secreto (no queda en el código)

Sube SOLO lo que está en el último commit de git (git archive): nada de .env, audios ni
carpetas locales. Las claves se leen del .env y nunca se imprimen.

Correr desde la raíz del repo:
    python -m deploy.publicar_hf
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi

RAIZ = Path(__file__).resolve().parent.parent
NOMBRE_SPACE = "tupa-bajo-la-lupa"


def main() -> None:
    load_dotenv(RAIZ / ".env")
    token, clave = os.environ.get("HF_TOKEN"), os.environ.get("ANTHROPIC_API_KEY")
    if not token or not clave:
        raise SystemExit("Falta HF_TOKEN o ANTHROPIC_API_KEY en el archivo .env")

    api = HfApi(token=token)
    repo = f"{api.whoami()['name']}/{NOMBRE_SPACE}"
    api.create_repo(repo, repo_type="space", space_sdk="docker", exist_ok=True)
    api.add_space_secret(repo, "ANTHROPIC_API_KEY", clave)

    with tempfile.TemporaryDirectory() as carpeta:
        archivo = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=RAIZ, check=True,
                                 capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archivo)) as tar:
            tar.extractall(carpeta, filter="data")
        shutil.copy(RAIZ / "deploy" / "README_space.md", Path(carpeta) / "README.md")  # ficha del Space
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, check=True,
                                capture_output=True, text=True).stdout.strip()
        api.upload_folder(folder_path=carpeta, repo_id=repo, repo_type="space",
                          commit_message=f"Publica el commit {commit} de GitHub")

    usuario, nombre = repo.split("/")
    print(f"Listo. Página del Space: https://huggingface.co/spaces/{repo}")
    print(f"App: https://{usuario.lower()}-{nombre}.hf.space (tarda unos 10 minutos en construirse)")


if __name__ == "__main__":
    main()
