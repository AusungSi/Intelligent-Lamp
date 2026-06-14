import time

from backend.services import lamp_service
from backend.services.db import fetch_one


def evaluate(derived_state, telemetry=None, policy=None):
    policy = policy or lamp_service.get_policy()
    config = policy["config"]
    if not policy["enabled"]:
        return {"type": "none", "reason": "policy_disabled"}

    presence = derived_state.get("presence_state")
    study_state = derived_state.get("study_state")
    env_labels = derived_state.get("env_labels") or []
    lux = (telemetry or {}).get("lux")
    now = int(time.time())

    if presence == "away":
        away_seconds = _estimate_away_seconds(derived_state.get("device_id"), now)
        if away_seconds >= int(config.get("away_off_seconds", 180)):
            return {"type": "set_light", "power": False, "reason": "away_timeout_off"}
        if away_seconds >= int(config.get("away_dim_seconds", 60)):
            return {
                "type": "set_light",
                "power": True,
                "brightness": int(config.get("dim_brightness", 20)),
                "color_temperature": int(config.get("rest_color_temperature", 3000)),
                "reason": "away_timeout_dim",
            }
        return {"type": "none", "reason": "away_waiting_grace"}

    if presence != "present":
        return {"type": "none", "reason": "presence_unknown"}

    brightness = int(config.get("normal_brightness", 55))
    if "too_dark" in env_labels or (lux is not None and float(lux) < float(config.get("too_dark_lux", 150))):
        brightness = int(config.get("too_dark_brightness", 80))

    color_temperature = int(config.get("day_study_color_temperature", 4300))
    if study_state == "idle":
        color_temperature = int(config.get("rest_color_temperature", 3000))

    return {
        "type": "set_light",
        "power": True,
        "brightness": brightness,
        "color_temperature": color_temperature,
        "reason": "present_study_lighting",
    }


def maybe_execute(derived_state, telemetry=None):
    policy = lamp_service.get_policy()
    binding_state = lamp_service.get_cached_state()
    if not binding_state["bound"]:
        action = evaluate(derived_state, telemetry, policy)
        return {"executed": False, "status": "skipped", "reason": "lamp_not_bound", "action": action}

    state = binding_state.get("state") or {}
    mode = state.get("mode")
    now = int(time.time())
    manual_until = state.get("manual_override_until") or 0
    if mode in ("off", "manual"):
        return {"executed": False, "status": "skipped", "reason": f"mode_{mode}"}
    if mode == "manual_override" and manual_until > now:
        return {"executed": False, "status": "skipped", "reason": "manual_override_active"}

    action = evaluate(derived_state, telemetry, policy)
    if action.get("type") != "set_light":
        return {"executed": False, "status": "skipped", "reason": action.get("reason"), "action": action}
    if _same_as_current(action, state):
        return {"executed": False, "status": "skipped", "reason": "state_already_matches", "action": action}
    age = lamp_service.latest_auto_command_age(action.get("reason"))
    debounce = int(policy["config"].get("debounce_seconds", 10))
    if age is not None and age < debounce:
        return {"executed": False, "status": "skipped", "reason": "debounced", "action": action}

    result = lamp_service.execute_lamp_action(
        {k: action[k] for k in ("power", "brightness", "color_temperature") if k in action},
        requested_by="auto",
        reason=action.get("reason"),
        mode="auto",
    )
    return {"executed": result.get("status") == "success", "action": action, **result}


def _same_as_current(action, state):
    for key in ("power", "brightness", "color_temperature"):
        if key in action and action[key] != state.get(key):
            return False
    return True


def _estimate_away_seconds(device_id, now):
    if not device_id:
        return 0
    last_present = fetch_one(
        """
        SELECT timestamp FROM derived_states
        WHERE device_id = ? AND presence_state = 'present'
        ORDER BY id DESC LIMIT 1
        """,
        (device_id,),
    )
    if not last_present:
        return 0
    return max(0, now - int(last_present["timestamp"]))
