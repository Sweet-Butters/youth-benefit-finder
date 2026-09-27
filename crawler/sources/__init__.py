"""Every source module has NAME, LABEL, NEEDS_KEY and fetch() -> list[Item]. Add new ones to ALL."""
from . import (bizinfo, certi, contest_allcon, contest_contestkorea, contest_linkareer, contest_thinkgood,
               contest_wevity, gov24, kosaf, kstartup, qnet, report, vms1365, volunteer)

# contest_allforyoung is left out: its robots.txt names AI crawlers to block, and it lists no eligibility.
ALL = [qnet, kosaf, certi, report, volunteer, vms1365, bizinfo, kstartup, gov24,
       contest_allcon, contest_contestkorea, contest_thinkgood, contest_wevity, contest_linkareer]
