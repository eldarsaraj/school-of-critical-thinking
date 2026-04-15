from django import template

register = template.Library()

_EFGH = {"A": "E", "B": "F", "C": "G", "D": "H"}


@register.filter
def display_letter(letter, question_number):
    """Return the display letter for a given internal letter (A-D) and question number.
    Odd questions: A/B/C/D. Even questions: E/F/G/H (official SHSAT alternating scheme)."""
    if not letter:
        return letter
    if int(question_number) % 2 == 0:
        return _EFGH.get(letter.upper(), letter)
    return letter.upper()
