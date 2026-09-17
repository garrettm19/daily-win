from sqlalchemy.orm import Session

from daily_win_api.db.session import SessionLocal
from daily_win_api.dev.seed import seed_development_data


def main() -> None:
    session: Session = SessionLocal()
    try:
        seed_development_data(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
