from typing import Annotated

from pydantic import StringConstraints

MAX_BIGINT = 2**63 - 1
DatabaseText = Annotated[str, StringConstraints(pattern=r"^[^\x00]*$")]
