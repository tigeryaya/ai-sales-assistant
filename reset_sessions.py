import asyncio

from agents import SQLiteSession


async def main():
    kevin_session = SQLiteSession(
        "kevin-session-001",
        "sales_sessions.db"
    )

    fresh_session = SQLiteSession(
        "fresh-session-001",
        "sales_sessions.db"
    )

    await kevin_session.clear_session()
    await fresh_session.clear_session()

    print("Test sessions cleared.")


asyncio.run(main())