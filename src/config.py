from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
# 역할: 환경변수를 코드에서 안전하게 다루기 위한 설정 데이터 구조다.
class Settings:
    gemini_api_key: str


# 역할: .env 파일을 읽어 KEY=VALUE 형태로 파싱한다.
def _load_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


# 역할: 실행에 필요한 설정값을 환경변수/파일에서 로드한다.
def load_settings() -> Settings:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    file_env = _load_env_file(env_path)
    if not file_env:
        shared_env = Path("/Users/parkgwanhoon/Desktop/geneisrap/.env")
        file_env = _load_env_file(shared_env)

    gemini_api_key = os.getenv("GEMINI_API_KEY", file_env.get("GEMINI_API_KEY", ""))

    if not gemini_api_key:
        missing = [
            name
            for name, value in [
                ("GEMINI_API_KEY", gemini_api_key),
            ]
            if not value
        ]
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    return Settings(gemini_api_key=gemini_api_key)
