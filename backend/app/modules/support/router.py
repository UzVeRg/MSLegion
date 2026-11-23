from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.modules.support.content import Language, SupportContent, get_content

router = APIRouter(prefix="/support", tags=["support"])


@router.get("", summary="Ответы на частые вопросы и контакты администрации")
async def support(
    settings: Annotated[Settings, Depends(get_settings)], language: Language = "ru"
) -> SupportContent:
    return get_content(language, settings.support_faq, settings.support_contacts)
