from datetime import timedelta


def generate_ics(session):
    """Generate RFC 5545 .ics content for an EventSession."""
    start = session.date_time
    end = start + timedelta(hours=1)

    def fmt(dt):
        return dt.strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//School of Critical Thinking//Events//EN",
        "BEGIN:VEVENT",
        f"DTSTART:{fmt(start)}",
        f"DTEND:{fmt(end)}",
        f"SUMMARY:{session.title}",
        f"DESCRIPTION:Join via Zoom: {session.zoom_link}",
        f"URL:{session.zoom_link}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines)
