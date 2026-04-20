import logging
from pathlib import Path
from pdfminer.high_level import extract_text

logger = logging.getLogger(__name__)

_resume_cache: str | None = None
_loaded: bool = False


def load_resume(path: str) -> str | None:
    """PDF 이력서를 읽어 텍스트로 반환한다. 실패 시 None 반환."""
    global _resume_cache, _loaded
    if _loaded:
        return _resume_cache

    _loaded = True
    file = Path(path)
    if not file.exists():
        logger.warning("이력서 파일 없음: %s — config.py 조건으로 폴백합니다.", path)
        return None

    try:
        text = extract_text(str(file))
        text = text.strip()
        if not text:
            logger.warning("이력서 텍스트 추출 결과 비어있음: %s", path)
            return None
        logger.info("이력서 로드 완료: %s (%d자)", path, len(text))
        _resume_cache = text
        return text
    except Exception as e:
        logger.error("이력서 로드 실패 (%s): %s", path, e)
        return None
