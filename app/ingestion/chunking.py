from __future__ import annotations

import re
from typing import Any


def chunk_manual_section(section: dict[str, Any]) -> list[dict[str, Any]]:
    """One chunk per manual section. Sections are already paragraph-sized."""
    content = (
        f"[{section['title']}]\n"
        f"Machine type: {section['machine_type']} | Component: {section['component']}\n\n"
        f"{section['content']}"
    )
    return [
        {
            "id": f"chunk-manual-{section['section_id']}",
            "source_type": "manual",
            "source_id": section["section_id"],
            "machine_id": None,
            "site": None,
            "content": content,
            "metadata": {
                "section_id": section["section_id"],
                "machine_type": section["machine_type"],
                "component": section["component"],
                "title": section["title"],
            },
        }
    ]


def chunk_ticket(ticket: dict[str, Any]) -> list[dict[str, Any]]:
    """One chunk per ticket. Encodes all structured fields as readable prose."""
    parts = [
        f"Incident {ticket['ticket_id']} — {ticket['machine_id']} ({ticket.get('site', '')})",
        f"Severity: {ticket['severity']} | Downtime: {ticket['downtime_hours']}h",
        f"Occurred: {ticket['occurred_at'][:10]}",
        f"Symptom: {ticket['symptom']}",
    ]
    if ticket.get("root_cause"):
        parts.append(f"Root cause: {ticket['root_cause']}")
    if ticket.get("resolution"):
        parts.append(f"Resolution: {ticket['resolution']}")
    if ticket.get("tags"):
        parts.append(f"Tags: {', '.join(ticket['tags'])}")

    return [
        {
            "id": f"chunk-ticket-{ticket['ticket_id']}",
            "source_type": "ticket",
            "source_id": ticket["ticket_id"],
            "machine_id": ticket["machine_id"],
            "site": ticket.get("site"),
            "content": "\n".join(parts),
            "metadata": {
                "ticket_id": ticket["ticket_id"],
                "severity": ticket["severity"],
                "occurred_at": ticket["occurred_at"],
                "downtime_hours": ticket["downtime_hours"],
                "tags": ticket.get("tags", []),
            },
        }
    ]


def chunk_operator_note(note: dict[str, Any]) -> list[dict[str, Any]]:
    """One chunk per operator note."""
    content = (
        f"Operator note [{note['note_id']}] — {note['machine_id']} ({note.get('site', '')})\n"
        f"Date: {note['created_at'][:10]} | Operator: {note['operator_id']}\n"
        f"{note['content']}"
    )
    return [
        {
            "id": f"chunk-note-{note['note_id']}",
            "source_type": "operator_note",
            "source_id": note["note_id"],
            "machine_id": note["machine_id"],
            "site": note.get("site"),
            "content": content,
            "metadata": {
                "note_id": note["note_id"],
                "operator_id": note["operator_id"],
                "created_at": note["created_at"],
            },
        }
    ]


def chunk_anomaly_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """One chunk per anomaly summary window."""
    chunk_id = (
        f"chunk-anomaly-{summary['machine_id']}-{summary['sensor_type']}-"
        f"{summary['window_start'][:10]}"
    )
    content = (
        f"Anomaly summary — {summary['machine_id']} | Sensor: {summary['sensor_type']}\n"
        f"Window: {summary['window_start'][:10]} to {summary['window_end'][:10]}\n"
        f"Anomaly count: {summary['anomaly_count']} | "
        f"Max deviation: {summary['max_deviation']} | Mean value: {summary['mean_value']}\n"
        f"{summary.get('description', '')}"
    )
    return [
        {
            "id": chunk_id,
            "source_type": "anomaly_summary",
            "source_id": chunk_id,
            "machine_id": summary["machine_id"],
            "site": None,
            "content": content,
            "metadata": {
                "sensor_type": summary["sensor_type"],
                "window_start": summary["window_start"],
                "window_end": summary["window_end"],
                "anomaly_count": summary["anomaly_count"],
            },
        }
    ]
