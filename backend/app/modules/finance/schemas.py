from datetime import date as CalendarDate

from pydantic import BaseModel, ConfigDict


class CheckInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: CalendarDate


class DailyReward(BaseModel):
    day: int
    amount: int


class WalletRead(BaseModel):
    balance: str
    date: CalendarDate
    streak: int
    day: int
    claimed_today: bool
    rewards: list[DailyReward]
    seconds_until_reset: int
