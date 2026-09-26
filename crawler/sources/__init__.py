"""Every source module has NAME, LABEL, NEEDS_KEY and fetch() -> list[Item]. Add new ones to ALL."""
from . import certi, kosaf, qnet, report, volunteer

ALL = [qnet, kosaf, certi, report, volunteer]
