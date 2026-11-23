from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Language = Literal["ru", "en"]
SUPPORT_BOT_USERNAME = "MsLegionSupport_bot"


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=180)
    answer: str = Field(min_length=1, max_length=1500)


class SupportContacts(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    telegram: str | None = Field(default=SUPPORT_BOT_USERNAME, pattern=r"^[A-Za-z0-9_]{5,32}$")
    discord: str | None = Field(
        default=None,
        pattern=(
            r"^https://(?:(?:discord\.gg/|discord\.com/invite/)[A-Za-z0-9_-]{1,100}"
            r"|discord\.com/users/[0-9]{17,20})$"
        ),
    )
    email: Annotated[str, StringConstraints(
        max_length=254,
        pattern=r"^[A-Za-z0-9_+.\-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$",
    )] | None = None


class Contact(BaseModel):
    channel: Literal["telegram", "discord", "email"]
    label: str
    url: str


class SupportContent(BaseModel):
    questions: list[Question]
    contacts: list[Contact]


def default_faq() -> dict[Language, list[Question]]:
    return {
        "ru": [
            Question(
                question="Что такое MSLegion?",
                answer="MSLegion объединяет игровые сообщества, игры, события и публикации "
                "в одном приложении Telegram.",
            ),
            Question(
                question="Как заработать LC?",
                answer="Откройте профиль в Mini App и заберите ежедневную награду. "
                "Отмечайтесь каждый день подряд, чтобы получать награды за серию.",
            ),
        ],
        "en": [
            Question(
                question="What is MSLegion?",
                answer="MSLegion brings gaming communities, games, events and posts "
                "together in one Telegram app.",
            ),
            Question(
                question="How can I earn LC?",
                answer="Open your profile in the Mini App and claim your daily reward. "
                "Check in on consecutive days to earn streak rewards.",
            ),
        ],
    }


def get_content(
    language: Language,
    faq: dict[Language, list[Question]] | None,
    settings: SupportContacts | None,
) -> SupportContent:
    if faq is None:
        faq = default_faq()
    if settings is None:
        settings = SupportContacts()
    contacts = []
    if settings.telegram:
        contacts.append(Contact(
            channel="telegram",
            label=f"@{settings.telegram}",
            url=f"https://t.me/{settings.telegram}",
        ))
    if settings.discord:
        contacts.append(Contact(channel="discord", label=settings.discord, url=settings.discord))
    if settings.email:
        contacts.append(Contact(
            channel="email", label=settings.email, url=f"mailto:{settings.email}",
        ))
    return SupportContent(questions=faq.get(language, faq.get("ru", [])), contacts=contacts)
