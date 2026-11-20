import argparse
import sys

import uvicorn

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Запуск API MSLegion")
    parser.add_argument(
        "--reload", action="store_true", help="перезапускать сервер при изменении исходников"
    )
    args = parser.parse_args()
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        loop="asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto",
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
