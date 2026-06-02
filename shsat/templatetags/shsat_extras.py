from django import template

register = template.Library()

_EFGH = {"A": "E", "B": "F", "C": "G", "D": "H"}


@register.filter
def duration(seconds):
    """Format a number of seconds as H:MM:SS."""
    if not seconds:
        return ""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}"


@register.filter
def display_letter(letter, question_number):
    """Return the display letter for a given internal letter (A-D) and question number.
    Odd questions: A/B/C/D. Even questions: E/F/G/H (official SHSAT alternating scheme)."""
    if not letter:
        return letter
    if int(question_number) % 2 == 0:
        return _EFGH.get(letter.upper(), letter)
    return letter.upper()
