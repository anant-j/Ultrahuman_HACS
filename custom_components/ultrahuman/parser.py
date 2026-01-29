"""Parser and sensor registry for Ultrahuman API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class UltrahumanMetric:
    key: str
    name: str


# 🔑 SINGLE SOURCE OF SENSOR DEFINITIONS
METRICS: tuple[UltrahumanMetric, ...] = (
    UltrahumanMetric("hr_last", "Heart Rate"),
    UltrahumanMetric("hrv_avg", "HRV"),
    UltrahumanMetric("spo2_avg", "SpO2"),
    UltrahumanMetric("steps", "Steps"),
    UltrahumanMetric("skin_temp", "Skin Temperature"),
    UltrahumanMetric("vo2_max", "VO2 Max"),
    UltrahumanMetric("sleep_start", "Sleep Start"),
    UltrahumanMetric("sleep_end", "Sleep End"),
    UltrahumanMetric("sleep_score", "Sleep Score"),
    UltrahumanMetric("total_sleep", "Total Sleep"),
)


class UltrahumanDataParser:
    """Parse Ultrahuman API payload into normalized values."""

    def __init__(self, raw: dict) -> None:
        self._raw = raw
        self._tz = raw.get("latest_time_zone")

        metrics_by_day = raw.get("metrics", {})
        self._day_key = next(iter(metrics_by_day), None)
        self._metrics = metrics_by_day.get(self._day_key, []) if self._day_key else []

    def _get_metric(self, metric_type: str) -> dict | None:
        return next(
            (m for m in self._metrics if m.get("type") == metric_type),
            None,
        )

    def _iso(self, ts: int | None) -> str | None:
        if not ts:
            return None
        return datetime.fromtimestamp(
            ts,
            tz=ZoneInfo(self._tz) if self._tz else None,
        ).isoformat()

    # 👇 ONLY THIS METHOD NEEDS EDITING TO ADD METRICS
    def get_value(self, key: str):
        if key == "hr_last":
            m = self._get_metric("hr")
            return m["object"].get("last_reading") if m else None

        if key == "hrv_avg":
            m = self._get_metric("hrv")
            return m["object"].get("avg") if m else None

        if key == "spo2_avg":
            m = self._get_metric("spo2")
            return m["object"].get("avg") if m else None

        if key == "steps":
            m = self._get_metric("steps")
            return m["object"].get("total") if m else None

        if key == "skin_temp":
            m = self._get_metric("temp")
            return m["object"].get("last_reading") if m else None

        if key == "vo2_max":
            m = self._get_metric("vo2_max")
            return m["object"].get("value") if m else None

        sleep = self._get_metric("sleep")
        sleep_obj = sleep.get("object") if sleep else {}

        if key == "sleep_start":
            return self._iso(sleep_obj.get("bedtime_start"))

        if key == "sleep_end":
            return self._iso(sleep_obj.get("bedtime_end"))

        if key == "sleep_score":
            return sleep_obj.get("sleep_score", {}).get("score")

        if key == "total_sleep":
            return sleep_obj.get("total_sleep", {}).get("minutes")

        return None
