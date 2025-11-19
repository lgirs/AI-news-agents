"""Prefect flows for orchestrating the agents."""
from __future__ import annotations

from prefect import flow
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from agents.publisher import load_digest, publish
from agents.reader import ReaderAgent
from agents.researcher import ResearcherAgent


@flow(name="researcher-flow")
def researcher_flow() -> None:
    ResearcherAgent().run()


@flow(name="reader-flow")
def reader_flow() -> str:
    agent = ReaderAgent()
    return str(agent.run())


@flow(name="publisher-flow")
def publisher_flow() -> str:
    digest = load_digest()
    path = publish(digest)
    return str(path)


if __name__ == "__main__":
    tz = "Europe/Helsinki"
    Deployment.build_from_flow(
        flow=researcher_flow,
        name="researcher-weekly",
        schedule=(CronSchedule(cron="0 8 * * MON", timezone=tz)),
    ).apply()
    Deployment.build_from_flow(
        flow=reader_flow,
        name="reader-daily",
        schedule=(CronSchedule(cron="0 8 * * 2-5", timezone=tz)),
    ).apply()
    Deployment.build_from_flow(
        flow=publisher_flow,
        name="publisher-daily",
        schedule=(CronSchedule(cron="5 8 * * 2-5", timezone=tz)),
    ).apply()
