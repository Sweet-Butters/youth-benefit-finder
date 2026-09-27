"""Audience tags (crawler/audience.py) and the contest merge (crawler/merge.py), on real item texts.

    python tests/test_audience.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler.audience import apply, tags_for  # noqa: E402
from crawler.merge import contest_norm, merge  # noqa: E402


def contest(source, title, target, **kw):
    return {"source": source, "source_id": kw.pop("sid", "1"), "type": "contest", "title": title,
            "provider": kw.pop("provider", ""), "target_text": target, "tags": kw.pop("tags", ["contest"]), **kw}


def kosaf(title, target, tags, **extra):
    return {"source": "kosaf", "source_id": "x", "type": "scholarship", "title": title, "provider": "",
            "target_text": target, "tags": tags, "extra": extra}


CASES = [
    # (name, record, must include, must not include)
    ("allcon 대학생", contest("allcon", "제24회 한국경제신문 경제논문 공모전", "대학생"),
     {"for:univ"}, {"for:all", "for:high", "for:middle"}),
    ("allcon 제한없음", contest("allcon", "제15회 도로경관디자인 대전", "제한없음", tags=["contest", "open_to_all"]),
     {"for:all"}, {"for:univ", "cond:region"}),
    ("allcon 중고등", contest("allcon", "x", "일반인, 대학생, 대학원생, 중학생, 고등학생"),
     {"for:middle", "for:high", "for:univ"}, {"for:all", "for:oos"}),
    ("contestkorea 누구나", contest("contestkorea", "제8회 뉴스읽기 뉴스일기 공모전",
                                     "누구나, 유치원, 초등학생, 중학생, 고등학생, 대학생, 대학원생, 일반인, 외국인"),
     {"for:all", "for:middle", "for:high", "for:univ"}, {"for:oos"}),
    ("contestkorea 초중", contest("contestkorea", "x", "초등학생, 중학생"), {"for:middle"}, {"for:high", "for:all"}),
    ("contestkorea 고등학생만", contest("contestkorea", "x", "고등학생"), {"for:high"}, {"for:middle", "for:univ"}),
    ("linkareer 대상 제한 없음", contest("linkareer", "제21회 공중화장실 혁신 아이디어 공모전", "대상 제한 없음"),
     {"for:all"}, {"for:univ"}),
    ("linkareer 청소년", contest("linkareer", "x", "청소년"), {"for:middle", "for:high"}, {"for:univ", "for:all"}),
    ("linkareer 청년 in title", contest("linkareer", "[서울특별시의회] 제5회 서울특별시의회 청년 학술 논문 공모전", "대학생"),
     {"for:univ", "for:young"}, {"for:high"}),
    ("thinkgood 동 연령대 청소년 = 학교 밖",
     contest("thinkgood", "x", "어린이, 초등학생, 중학생, 고등학생, 동 연령대 청소년, 대학생, 대학원생, 일반인, 제한 없음"),
     {"for:all", "for:oos", "for:middle", "for:high", "for:univ"}, set()),
    ("thinkgood 고등·대학", contest("thinkgood", "제 2회 직스캐드 AX 경진대회", "고등학생, 대학생"),
     {"for:high", "for:univ"}, {"for:middle", "for:all"}),
    ("wevity 청소년, 대학생", contest("wevity", "2026 전북 청소년 평화통일 퍼포먼스 페스타", "청소년, 대학생"),
     {"for:middle", "for:high", "for:univ"}, {"for:all"}),
    ("wevity 대학생 멘토 (title 초등 ignored)", contest("wevity", "2026학년도 학교폭력 피해학생 대상 대학생 멘토 모집 (제주센터)", "대학생"),
     {"for:univ"}, {"for:middle", "for:high"}),
    ("1365 youth only (age_max 18)",
     {"source": "vms1365", "type": "experience", "title": "2026년 4분기 불암도서관 자원봉사활동 (청소년, 주말 오전 10:00~12:00)",
      "age_max": 18, "target_text": "청소년 가능 (1365 청소년가능 표시)", "tags": ["volunteer"]},
     {"for:middle", "for:high"}, {"for:all", "for:univ"}),
    ("1365 open to all; title about who is served is not a condition",
     {"source": "vms1365", "type": "experience", "title": "[종촌노인주간보호센터] 어르신 활동보조 및 장애인 이동지원",
      "target_text": "청소년 가능 (1365 청소년가능 표시), 성인 가능", "tags": ["volunteer", "open_to_all"]},
     {"for:all"}, {"cond:special", "for:middle"}),
    ("certi 중학생 14-16", {"source": "certi", "type": "experience", "title": "진로캠프(중학교 2박3일)", "age_min": 14,
                          "age_max": 16, "target_text": "중학생 (중(320명))", "tags": ["certified"]},
     {"for:middle"}, {"for:high"}),
    ("certi 고등학생 17-19", {"source": "certi", "type": "experience", "title": "x", "age_min": 17, "age_max": 19,
                            "target_text": "고등학생 (고(300명))", "tags": ["certified"]},
     {"for:high"}, {"for:middle", "for:univ"}),
    ("age 13-18, no text", {"source": "other", "type": "experience", "title": "x", "age_min": 13, "age_max": 18, "tags": []},
     {"for:middle", "for:high"}, {"for:univ"}),
    ("volunteer 청소년 자원봉사", {"source": "volunteer", "type": "experience", "title": "늘스마일 자원봉사단",
                              "target_text": "청소년 자원봉사", "tags": ["volunteer"]},
     {"for:middle", "for:high"}, {"for:all"}),
    ("qnet exam open to all", {"source": "qnet", "type": "resource", "title": "미용사(일반) 2026년 37회 필기 원서접수",
                               "tags": ["qnet:7937", "open_to_all", "field:beauty", "out_of_school_ok"]},
     {"for:all", "for:oos"}, {"for:high"}),
    ("kstartup 20-39 대학생", {"source": "kstartup", "type": "support", "title": "[창업] 창업가를 위한 가격 전략 실전",
                              "age_min": 20, "age_max": 39, "target_text": "대상: 대학생, 일반인. 대상연령: 만 20세 이상 ~ 만 39세 이하.",
                              "tags": ["startup"]},
     {"for:univ", "for:young"}, {"for:high", "cond:region"}),
    ("bizinfo 청년 + 거주지", {"source": "bizinfo", "type": "support", "title": "[전북] 군산시 2026년 청년창업플랫폼 예비창업자 모집 공고",
                              "target_text": "창업벤처 공고일 현재 주민등록상 주소지가 군산시로 되어 있는 자로, 외식 창업을 희망하는 만 19세 이상 ~ 39세 이하의 개인",
                              "tags": ["startup"]},
     {"for:young", "cond:region"}, {"for:high", "cond:income"}),
    ("kosaf 대학생 + income/residence/grade columns",
     kosaf("재단법인 안산인재육성재단 대학생 본인부담 등록금 반값 지원",
           "대학생 대상 · 대학: 4년제, 기술대학, 원격대학, 전문대 · 학년: 제한 없음 · 학과: 제한 없음 · 29세 이하 대학생",
           ["kosaf:univ"], income="국민기초생활수급자 / 차상위계층 / 법정 한부모 가정 학생 / 소득 1~6구간 가정 학생",
           residence="공고일 및 지급일 현재 안산시에 3년 이상 계속 주민등록을 두거나", aid_kind="지역연고",
           grade="재학생:직전학기 12학점 이상 이수하여 100분위 성적 60점(D학점)이상 취득"),
     {"for:univ", "cond:income", "cond:region", "cond:grade", "cond:special"}, {"for:all", "for:high"}),
    ("kosaf 학년: 제한 없음 is not 누구나",
     kosaf("x", "고등학생 대상 · 학교: 제한 없음 · 학년: 제한 없음", ["kosaf:hs"]),
     {"for:high"}, {"for:all", "cond:region", "cond:income", "cond:grade"}),
    ("kosaf preference is not a requirement",
     kosaf("x", "대학생 대상 · 29세 이하 대학생 / 3자녀이상/ 장애인/ 저소득층 학생 우선지원", ["kosaf:univ"]),
     {"for:univ"}, {"cond:special", "cond:income"}),
    ("kosaf 중3~고2 (hs file includes middle)",
     kosaf("우체국공익재단 희망장학금", "고등학생 대상 · 학교: 제한 없음 · 대한민국 국적을 가진 국내 중학교 3학년 또는 고등학교 1~2학년에 재학중인 학생",
           ["kosaf:hs"]),
     {"for:middle", "for:high"}, {"for:univ"}),
    ("kosaf 학교 밖 청소년",
     kosaf("광주남구장학회 학교밖청소년장학", "고등학생 대상 · 2024년도 초졸/중졸/고졸 검정고시에 응시하여 합격한 자로서 학교 밖 청소년 지원 시설장의 추천을 받은 자",
           ["kosaf:hs"]),
     {"for:oos", "for:high"}, {"for:univ"}),
    ("kosaf 다문화 in income column",
     kosaf("x", "고등학생 대상", ["kosaf:hs"], income="다문화 가정의 자녀인 학생"),
     {"cond:special"}, {"cond:income"}),
    ("kosaf 성적우수 aid kind + 기관에 확인 필요",
     kosaf("x", "대학생 대상", ["kosaf:univ"], aid_kind="성적우수", income="기관에 확인 필요", residence="기관에 확인 필요"),
     {"cond:grade"}, {"cond:income", "cond:region"}),
    ("kosaf 북한이탈주민", kosaf("남북하나재단 북한이탈주민장학", "고등학생 대상 · 보호결정을 받은 북한이탈주민 / 국내 정규 고등학교 재학생", ["kosaf:hs"]),
     {"cond:special", "for:high"}, {"for:oos"}),
    ("kosaf 학과 성적 무관", kosaf("x", "대학생 대상", ["kosaf:univ"], grade="학과 성적 무관"), set(), {"cond:grade"}),
    ("thinkgood 거주지 관계없이 is not a region limit",
     contest("thinkgood", "2026 대한민국 SF판타지 웹소설 공모전",
             "중학생, 고등학생, 동 연령대 청소년, 대학생, 대학원생, 일반인, 기타 (국적, 거주지, 경력에 관계없이 만 14세 이상인 자)"),
     {"for:middle", "for:high", "for:oos", "for:univ"}, {"cond:region"}),
    ("thinkgood 경기도 소재 대학", contest("thinkgood", "2027 경기도 대학생 자율주행 경진대회",
                                        "대학생, 기타 (경기도 소재 대학(전문대 포함)에 재학중인 학부생)"),
     {"for:univ", "cond:region"}, {"for:high"}),
    ("kosaf nationwide residence", kosaf("x", "대학생 대상", ["kosaf:univ"], residence="대한민국 거주"), set(), {"cond:region"}),
]


def test_audience():
    for name, rec, must, must_not in CASES:
        got = set(tags_for(rec))
        assert must <= got, f"{name}: missing {must - got} (got {sorted(got)})"
        assert not (must_not & got), f"{name}: unexpected {must_not & got} (got {sorted(got)})"


def test_apply_idempotent():
    rec = contest("linkareer", "x", "청소년", tags=["contest", "for:univ", "cond:grade"])
    apply(rec)
    once = list(rec["tags"])
    apply(rec)
    assert rec["tags"] == once
    assert "for:univ" not in once and "cond:grade" not in once and once[0] == "contest"


def test_contest_norm():
    assert contest_norm("제1회 [자갈치문학상] 공모") == contest_norm("제1회 자갈치문학상 공모") == "자갈치문학상"
    assert contest_norm("[청주공예비엔날레] 2027 청주국제공예공모전") == contest_norm("2027 청주국제공예공모전")
    assert contest_norm("2026 ‘0924 영상제’ 영상 공모전 | 최고 상금 100만 원! (~10/17)") == contest_norm("2026 ‘0924 영상제’ 영상 공모전")
    assert contest_norm("【FOCUS ON 진천 : 빛나는 순간을 기록하다】 2026년 진천군 SNS 영상 공모전") == contest_norm("2026년 진천군 SNS 영상 공모전 공고")
    assert len(contest_norm("2026 영상 공모전")) < 6  # too generic to merge on


def test_merge_quoted_name():
    a = contest("thinkgood", "'더로드셰프 한강' 청년 셰프·외식 창업가 모집", "일반인", sid="110988", provider="한국문화기획학교",
                apply_end="2026-09-27")
    b = contest("linkareer", "'더로드쉐프 한강' 전국 청년 셰프 및 외식 창업가 모집", "대상 제한 없음", sid="9", provider="대행사",
                apply_end="2026-09-27")
    c = contest("wevity", "[과학기술정보통신부] 2026 AI 활용 아이디어 공모전", "제한없음", sid="1", apply_end="2026-10-02")
    d = contest("allcon", "[과학기술정보통신부] 2026 정보보호 정책제안 공모전", "제한없음", sid="2", apply_end="2026-10-02")
    out = merge([], [a, b, c, d], "2026-09-27")
    assert len(out) == 3, [r["title"] for r in out]  # host brackets alone never merge
    kept = next(r for r in out if "also_in" in r)
    assert kept["sources"] == ["thinkgood", "linkareer"] and kept["also_in"] == ["linkareer:9"]


def test_merge_contests():
    a = contest("thinkgood", "2027 청주국제공예공모전", "대학생, 대학원생, 일반인", sid="108733", provider="청주시", apply_end="2027-05-05")
    b = contest("linkareer", "[청주공예비엔날레] 2027 청주국제공예공모전", "대상 제한 없음", sid="338658",
                provider="청주공예비엔날레 조직위원회", apply_end="2027-05-05")
    c = contest("linkareer", "2027 청주국제공예공모전", "대상 제한 없음", sid="338666", provider="청주공예비엔날레조직위원회")  # no deadline
    d = contest("allcon", "2026 영상 공모전", "제한없음", sid="1", provider="A시", apply_end="2026-10-01")  # generic: stays
    e = contest("wevity", "2026 영상 공모전", "제한없음", sid="2", provider="B재단", apply_end="2026-10-01")
    g = {"source": "certi", "source_id": "9", "type": "experience", "title": "2027 청주국제공예", "provider": "",
         "apply_end": "2027-05-05"}  # not a contest: never merged by the loose rule
    out = merge([], [a, b, c, d, e, g], "2026-09-27")
    keys = {f"{r['source']}:{r['source_id']}" for r in out}
    assert keys == {"thinkgood:108733", "allcon:1", "wevity:2", "certi:9"}, keys
    kept = next(r for r in out if r["source_id"] == "108733")
    assert kept["also_in"] == ["linkareer:338658", "linkareer:338666"]
    assert kept["sources"] == ["thinkgood", "linkareer"]


def test_merge_contest_other_deadline():
    a = contest("thinkgood", "2027 청주국제공예공모전", "제한없음", sid="1", provider="청주시", apply_end="2027-05-05")
    b = contest("wevity", "2027 청주국제공예공모전", "제한없음", sid="2", provider="청주시청", apply_end="2027-06-01")
    c = contest("linkareer", "2027 청주국제공예공모전", "제한없음", sid="3", provider="대행사")  # no deadline, two candidates
    out = merge([], [a, b, c], "2026-09-27")
    assert len(out) == 3 and not any("also_in" in r for r in out)


if __name__ == "__main__":
    tests = [test_audience, test_apply_idempotent, test_contest_norm, test_merge_contests, test_merge_contest_other_deadline,
             test_merge_quoted_name]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"{len(CASES)} audience cases + {len(tests) - 1} merge/apply tests passed")
