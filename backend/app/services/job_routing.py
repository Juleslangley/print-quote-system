from __future__ import annotations

from typing import TypedDict


class JobType:
    LARGE_FORMAT_SHEET = "LARGE_FORMAT_SHEET"
    LARGE_FORMAT_ROLL = "LARGE_FORMAT_ROLL"
    LITHO_SHEET = "LITHO_SHEET"
    DIGITAL_SHEET = "DIGITAL_SHEET"


ALL_JOB_TYPES = {
    JobType.LARGE_FORMAT_SHEET,
    JobType.LARGE_FORMAT_ROLL,
    JobType.LITHO_SHEET,
    JobType.DIGITAL_SHEET,
}


class ProductionLane:
    LF_SHEET = "LF_SHEET"
    LF_ROLL = "LF_ROLL"
    LITHO_OUTSOURCE = "LITHO_OUTSOURCE"
    DIGITAL_SHEET_PRESS = "DIGITAL_SHEET_PRESS"


class MachineKey:
    ACUITY_PRIME = "ACUITY_PRIME"  # Fuji - deprecated from defaults, kept for history
    NYALA = "NYALA"  # SwissQ Nyala 5 (sheet)
    HP_SC_8600 = "HP_SC_8600"  # HP SC 8600 (roll)


class JobTypeDefaults(TypedDict):
    lane: str
    material_mode: str
    default_waste_pct: float
    default_setup_minutes: int
    default_machine_key: str | None
    notes: str


JOBTYPE_DEFAULTS: dict[str, JobTypeDefaults] = {
    JobType.LARGE_FORMAT_SHEET: {
        "lane": ProductionLane.LF_SHEET,
        "material_mode": "SHEET",
        "default_waste_pct": 0.10,
        "default_setup_minutes": 15,
        "default_machine_key": MachineKey.NYALA,
        "notes": "SwissQ Nyala 5 default lane",
    },
    JobType.LARGE_FORMAT_ROLL: {
        "lane": ProductionLane.LF_ROLL,
        "material_mode": "ROLL",
        "default_waste_pct": 0.15,
        "default_setup_minutes": 20,
        "default_machine_key": MachineKey.HP_SC_8600,
        "notes": "HP SC 8600 default lane",
    },
    JobType.LITHO_SHEET: {
        "lane": ProductionLane.LITHO_OUTSOURCE,
        "material_mode": "SHEET",
        "default_waste_pct": 0.05,
        "default_setup_minutes": 30,
        "default_machine_key": None,
        "notes": "Litho outsource by default",
    },
    JobType.DIGITAL_SHEET: {
        "lane": ProductionLane.DIGITAL_SHEET_PRESS,
        "material_mode": "SHEET",
        "default_waste_pct": 0.05,
        "default_setup_minutes": 10,
        "default_machine_key": None,
        "notes": "Digital sheet press lane",
    },
}


JOB_TYPE_LABELS: dict[str, str] = {
    JobType.LARGE_FORMAT_SHEET: "Large Format sheet",
    JobType.LARGE_FORMAT_ROLL: "Large Format Roll",
    JobType.LITHO_SHEET: "Litho sheet",
    JobType.DIGITAL_SHEET: "Digital sheet",
}


def normalize_job_type(job_type: str | None) -> str:
    if not job_type:
        return JobType.LARGE_FORMAT_SHEET
    candidate = str(job_type).strip().upper()
    if candidate in ALL_JOB_TYPES:
        return candidate
    return JobType.LARGE_FORMAT_SHEET


def get_jobtype_defaults(job_type: str | None) -> JobTypeDefaults:
    normalized = normalize_job_type(job_type)
    return JOBTYPE_DEFAULTS[normalized]


def label_for_job_type(job_type: str | None) -> str:
    normalized = normalize_job_type(job_type)
    return JOB_TYPE_LABELS.get(normalized, JOB_TYPE_LABELS[JobType.LARGE_FORMAT_SHEET])


def is_roll_job(job_type: str | None) -> bool:
    normalized = normalize_job_type(job_type)
    return normalized == JobType.LARGE_FORMAT_ROLL


def apply_defaults_to_item_options(options: dict | None, job_type: str | None) -> dict:
    defaults = get_jobtype_defaults(job_type)
    out = dict(options or {})
    if "waste_pct" not in out or out.get("waste_pct") is None:
        out["waste_pct"] = defaults["default_waste_pct"]
    if "setup_minutes" not in out or out.get("setup_minutes") is None:
        out["setup_minutes"] = defaults["default_setup_minutes"]
    return out

