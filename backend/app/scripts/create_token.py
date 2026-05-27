from argparse import ArgumentParser

from app.core.database import SessionLocal
from app.core.security import generate_token, hash_token
from app.models.api_token import ApiToken


def main() -> None:
    parser = ArgumentParser(description="Create an API token and print it once.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", default=None)
    args = parser.parse_args()

    token = generate_token()
    with SessionLocal() as db:
        db.add(
            ApiToken(
                name=args.name,
                token_hash=hash_token(token),
                enabled=True,
                description=args.description,
            )
        )
        db.commit()

    print("API token created. It is shown once:")
    print(token)


if __name__ == "__main__":
    main()
