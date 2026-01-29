"""Sensor platform for Ultrahuman Ring integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

import aiohttp

DOMAIN = "ultrahuman"
_LOGGER = logging.getLogger(__name__)

API_URL = "https://partner.ultrahuman.com/api/v1/partner/daily_metrics"

# (Name, metric_type, value_key, is_timestamp)
SENSORS: tuple[tuple[str, str, str, bool], ...] = (
    ("Night Resting HR", "night_rhr", "avg", False),
    ("Sleep HRV", "avg_sleep_hrv", "value", False),
    ("Sleep RHR", "sleep_rhr", "value", False),
    ("Recovery Index", "recovery_index", "value", False),
    ("Movement Index", "movement_index", "value", False),
    ("Active Minutes", "active_minutes", "value", False),
    ("VO2 Max", "vo2_max", "value", False),
    ("Sleep Start", "sleep", "bedtime_start", True),
    ("Sleep End", "sleep", "bedtime_end", True),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ultrahuman sensors from a config entry."""
    api_token = entry.data["api_token"]

    async def _fetch_data():
        today = datetime.now().strftime("%Y-%m-%d")
        headers = {
            "Authorization": api_token,
            "Accept": "application/json",
        }
        params = {"date": today}

        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers, params=params, timeout=20) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                return payload["data"]

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Ultrahuman Ring",
        update_method=_fetch_data,
        update_interval=timedelta(minutes=60),
    )

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        UltrahumanSensor(
            entry.entry_id,
            coordinator,
            name,
            metric_type,
            value_key,
            is_timestamp,
        )
        for name, metric_type, value_key, is_timestamp in SENSORS
    )


class UltrahumanSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Ultrahuman sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        coordinator: DataUpdateCoordinator,
        name: str,
        metric_type: str,
        value_key: str,
        is_timestamp: bool,
    ) -> None:
        super().__init__(coordinator)
        self._metric_type = metric_type
        self._value_key = value_key
        self._is_timestamp = is_timestamp

        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{metric_type}_{value_key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "ultrahuman_ring")},
            name="Ultrahuman Ring",
            manufacturer="Ultrahuman",
            model="Ring AIR",
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None

        metrics_by_day = self.coordinator.data.get("metrics", {})
        if not metrics_by_day:
            return None

        # API date key may not match local date; take the only returned day
        day_key = next(iter(metrics_by_day), None)
        if not day_key:
            return None

        metrics = metrics_by_day.get(day_key, [])
        metric = next(
            (m for m in metrics if m.get("type") == self._metric_type),
            None,
        )

        if not metric:
            return None

        obj = metric.get("object", {})
        value = obj.get(self._value_key)

        if value is None:
            return None

        if self._is_timestamp:
            tz = self.coordinator.data.get("latest_time_zone")
            try:
                return datetime.fromtimestamp(
                    value,
                    tz=ZoneInfo(tz) if tz else None,
                ).isoformat()
            except Exception:
                return None

        return value
