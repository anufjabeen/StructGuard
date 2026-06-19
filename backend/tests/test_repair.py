from app.core.repair import JsonRepairer


def test_repairer_maps_triaged_to_incident_status() -> None:
    schema = {
        "properties": {
            "status": {
                "type": "string",
                "enum": ["open", "investigating", "resolved"],
            }
        }
    }

    repaired, repairs = JsonRepairer().repair({"status": "triaged"}, schema)

    assert repaired["status"] == "investigating"
    assert "REPAIRED_ENUM:status" in repairs


def test_repairer_keeps_valid_bug_status() -> None:
    schema = {
        "properties": {
            "status": {
                "type": "string",
                "enum": ["new", "triaged", "in_progress", "fixed", "wont_fix"],
            }
        }
    }

    repaired, repairs = JsonRepairer().repair({"status": "triaged"}, schema)

    assert repaired["status"] == "triaged"
    assert repairs == []


def test_repairer_does_not_fuzzy_match_short_enum_values() -> None:
    schema = {
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
            }
        }
    }

    repaired, repairs = JsonRepairer().repair({"severity": "lo"}, schema)

    assert repaired["severity"] == "lo"
    assert repairs == []


def test_repairer_does_not_parse_integer_like_datetime() -> None:
    schema = {
        "properties": {
            "reported_at": {
                "type": "string",
                "format": "date-time",
            }
        }
    }

    repaired, repairs = JsonRepairer().repair({"reported_at": "500"}, schema)

    assert repaired["reported_at"] == "500"
    assert repairs == []
