import streamlit as st
import requests
import uuid
import html as html_lib
from datetime import datetime, timedelta
import pytz

BASE_URL = "https://welplus.welstory.com"
RESTAURANT_ID = "REST000076"
DEVICE_ID = str(uuid.uuid4())
KST = pytz.timezone("Asia/Seoul")

MEAL_TIMES = [("1", "🌅 아침"), ("2", "☀️ 점심"), ("3", "🌙 저녁")]


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def korea_today():
    return datetime.now(KST).date()


def date_to_str(d):
    return d.strftime("%Y%m%d")


def date_label(d):
    days = ["월", "화", "수", "목", "금", "토", "일"]
    return f"{d.month}월 {d.day}일 ({days[d.weekday()]})"


def parse_kcal(val):
    if not val:
        return None
    try:
        return int(float(str(val).replace(",", "")))
    except Exception:
        return None


# ── 방문자 카운터 ─────────────────────────────────────────────────────────────

_COUNTER_NS = "yardmenu-rogermostwanted"


def _hit_counter(key: str) -> int:
    try:
        r = requests.get(f"https://api.counterapi.dev/v1/{_COUNTER_NS}/{key}/up", timeout=3)
        return r.json().get("count", -1) if r.ok else -1
    except Exception:
        return -1


def fetch_visitor_counts() -> tuple:
    today_key = "today-" + datetime.now(tz=KST).strftime("%Y-%m-%d")
    today = _hit_counter(today_key)
    total = _hit_counter("total")
    return today, total


# ── API ──────────────────────────────────────────────────────────────────────

def do_login():
    r = requests.post(
        f"{BASE_URL}/login",
        headers={
            "User-Agent": "Welplus",
            "X-Device-Id": DEVICE_ID,
            "X-Autologin": "N",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "username": st.secrets["WELSTORY_USERNAME"],
            "password": st.secrets["WELSTORY_PASSWORD"],
            "remember-me": "false",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.headers["Authorization"]


def api_get(token, path, params=None):
    r = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        headers={"User-Agent": "Welplus", "X-Device-Id": DEVICE_ID, "Authorization": token},
        timeout=10,
    )
    r.raise_for_status()
    if not r.text.strip():
        raise ValueError("empty_body")
    return r.json()


def fetch_dishes(token, date_str, meal_id):
    data = api_get(token, "/api/meal", {
        "menuDt": date_str,
        "menuMealType": meal_id,
        "restaurantCode": RESTAURANT_ID,
    })
    return data.get("data", {}).get("mealList", [])


def fetch_course_detail(token, date_str, meal_id, hall_no, course_type):
    data = api_get(token, "/api/meal/detail/nutrient", {
        "menuDt": date_str,
        "hallNo": hall_no,
        "menuCourseType": course_type,
        "menuMealType": meal_id,
        "restaurantCode": RESTAURANT_ID,
    })
    return data.get("data", []) or []


def fetch_image(url, token):
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Welplus", "Authorization": token},
            timeout=5,
        )
        if r.ok and r.content:
            return r.content
    except Exception:
        pass
    return None


def get_dishes_with_relogin(token, date_str, meal_id):
    try:
        return fetch_dishes(token, date_str, meal_id), token
    except ValueError:
        new_token = do_login()
        st.session_state.token = new_token
        return fetch_dishes(new_token, date_str, meal_id), new_token


# ── 메뉴 데이터 파싱 ──────────────────────────────────────────────────────────

def group_into_courses(dishes):
    groups = {}
    for d in dishes:
        key = f"{d['hallNo']}-{d['menuCourseType']}"
        groups.setdefault(key, []).append(d)
    return list(groups.values())


def is_takeout(dishes):
    first = dishes[0]
    if first.get("salesType", "").startswith("T"):
        return True
    return any(
        ("[" in d["menuName"] and "Coin" in d["menuName"]) or "도시락" in d["menuName"]
        for d in dishes
    )


def main_dish_name(dishes):
    main = next((d for d in dishes if d.get("typicalMenu") == "Y"), dishes[0])
    return main["menuName"]


def course_label(dishes):
    return dishes[0].get("courseTxt", "")


def course_image_url(dishes):
    first = dishes[0]
    cd = first.get("photoCd", "")
    url = first.get("photoUrl", "")
    return (url + cd) if cd and url else None


# ── 렌더링 헬퍼 ──────────────────────────────────────────────────────────────

def render_dish_table(label, main_name, dish_names):
    rows = ""
    if label:
        rows += (
            f"<tr><td style='padding:10px 12px;border-bottom:1px solid var(--wm-border);"
            f"font-weight:600;color:var(--wm-text);'>"
            f"&lt;{html_lib.escape(label)}&gt;{html_lib.escape(main_name)}</td></tr>"
        )
    for n in dish_names:
        rows += (
            f"<tr><td style='padding:9px 12px;border-bottom:1px solid var(--wm-border);"
            f"color:var(--wm-text-sub);'>{html_lib.escape(n)}</td></tr>"
        )
    st.markdown(
        f"""
        <table style="width:100%;border-collapse:collapse;font-size:14px;margin-top:6px;">
            <thead>
                <tr>
                    <th style="text-align:left;padding:8px 12px;border-bottom:2px solid var(--wm-border);
                               color:var(--wm-text-muted);font-size:12px;font-weight:600;letter-spacing:0.5px;">
                        항목
                    </th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def render_course(course, date_str, meal_id, token):
    name = main_dish_name(course)
    label = course_label(course)
    kcal = parse_kcal(course[0].get("sumKcal"))
    img_url = course_image_url(course)
    hall_no = course[0].get("hallNo", "")
    course_type = course[0].get("menuCourseType", "")

    dish_names = [d["menuName"] for d in course]
    if hall_no and course_type:
        try:
            detail = fetch_course_detail(token, date_str, meal_id, hall_no, course_type)
            if detail:
                dish_names = [item["menuName"] for item in detail]
                main_item = next((item for item in detail if item.get("typicalMenu") == "Y"), None)
                if main_item:
                    name = main_item["menuName"]
        except Exception:
            pass

    kcal_str = f"&nbsp;&nbsp;<span style='color:var(--wm-text-muted);font-size:13px;'>{kcal} kcal</span>" if kcal else ""
    header_label = f"<span style='background:var(--wm-badge-bg);color:var(--wm-badge-color);font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600;margin-right:8px;'>{html_lib.escape(label)}</span>" if label else ""
    header_name = f"<strong>{html_lib.escape(name)}</strong>"

    img_data = fetch_image(img_url, token) if img_url else None

    st.markdown(
        f"<div style='margin-bottom:4px;'>{header_label}{header_name}{kcal_str}</div>",
        unsafe_allow_html=True,
    )

    if img_data:
        st.image(img_data, use_container_width=True)

    render_dish_table(label, name, dish_names)
    st.markdown("<hr style='margin:12px 0;border:none;border-top:1px solid var(--wm-border);'>", unsafe_allow_html=True)


# ── 페이지 설정 ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="삼성중공업 식단", page_icon="🍱", layout="centered")

# ── CSS ──────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Streamlit CSS 변수 기반 동적 색상 (Settings 토글에 자동 반응) */
:root {
    --wm-badge-bg:    color-mix(in srgb, var(--primary-color) 12%, var(--secondary-background-color));
    --wm-badge-color: var(--primary-color);
    --wm-text:        var(--text-color);
    --wm-text-sub:    color-mix(in srgb, var(--text-color) 75%, transparent);
    --wm-text-muted:  color-mix(in srgb, var(--text-color) 45%, transparent);
    --wm-border:      var(--secondary-background-color);
    --wm-footer:      color-mix(in srgb, var(--text-color) 40%, transparent);
}

/* Streamlit 상단 헤더(Deploy 바) 높이만큼 여백 */
.block-container {
    padding-top: 3.5rem !important;
}

/* 날짜 네비 한 줄 강제 */
[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    gap: 4px !important;
    align-items: center !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: 0 !important;
    flex-shrink: 1 !important;
}
@media (max-width: 640px) {
    [data-testid="stHorizontalBlock"] button {
        padding: 6px 4px !important;
        font-size: 13px !important;
    }
}

/* 탭 스타일 라디오 */
div[data-testid="stRadio"] > div {
    display: flex;
    flex-wrap: nowrap;
    justify-content: center;
    gap: 0;
    border-bottom: 2px solid var(--secondary-background-color);
    margin-bottom: 0;
}
div[data-testid="stRadio"] > div > label {
    flex: 0 0 auto;
    text-align: center;
    padding: 6px 20px;
    border-bottom: 3px solid transparent;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    opacity: 0.5;
    margin-bottom: -2px;
    background: transparent;
    transition: opacity 0.15s;
    white-space: nowrap;
}
div[data-testid="stRadio"] > div > label:has(input:checked) {
    border-bottom: 3px solid var(--primary-color);
    opacity: 1;
    color: var(--primary-color);
    font-weight: 700;
}
div[data-testid="stRadio"] > div > label > div:first-child { display: none; }
div[data-testid="stRadio"] > div > label p { margin: 0; }
</style>
""", unsafe_allow_html=True)

# ── 로그인 ───────────────────────────────────────────────────────────────────

if "token" not in st.session_state:
    with st.spinner("로그인 중..."):
        try:
            st.session_state.token = do_login()
        except Exception as e:
            st.error(f"로그인 실패: {e}")
            st.stop()

# ── 날짜 네비게이션 ──────────────────────────────────────────────────────────

if "sel_date" not in st.session_state:
    st.session_state.sel_date = korea_today()

meal_labels = [label for _, label in MEAL_TIMES]
today = korea_today()
sel = st.session_state.sel_date
diff = (sel - today).days

if diff == 0:
    badge = " <span style='font-size:12px;color:#1a73e8;font-weight:700;'>(오늘)</span>"
elif diff == 1:
    badge = " <span style='font-size:12px;color:#34a853;font-weight:700;'>(내일)</span>"
elif diff == -1:
    badge = " <span style='font-size:12px;color:#9aa0a6;font-weight:700;'>(어제)</span>"
else:
    badge = ""

col_today, col_prev, col_date, col_next = st.columns([1.5, 1, 4, 1])
with col_today:
    if st.button("오늘", use_container_width=True, disabled=(diff == 0)):
        st.session_state.sel_date = today
        st.session_state.meal_radio = meal_labels[1]
        st.rerun()
with col_prev:
    if st.button("◀", use_container_width=True):
        st.session_state.sel_date -= timedelta(days=1)
        st.session_state.meal_radio = meal_labels[1]
        st.rerun()
with col_date:
    st.markdown(
        f"<div style='text-align:center;font-size:15px;font-weight:600;"
        f"white-space:nowrap;line-height:38px;'>{date_label(sel)}{badge}</div>",
        unsafe_allow_html=True,
    )
with col_next:
    if st.button("▶", use_container_width=True):
        st.session_state.sel_date += timedelta(days=1)
        st.session_state.meal_radio = meal_labels[1]
        st.rerun()

date_str = date_to_str(sel)

st.divider()

# ── 아침/점심/저녁 탭 ────────────────────────────────────────────────────────

if "meal_radio" not in st.session_state:
    st.session_state.meal_radio = meal_labels[1]

selected_label = st.radio(
    "식사 시간",
    options=meal_labels,
    key="meal_radio",
    horizontal=True,
    label_visibility="collapsed",
)
meal_id = next(mid for mid, lbl in MEAL_TIMES if lbl == selected_label)

# ── 메뉴 컨텐츠 ──────────────────────────────────────────────────────────────

token = st.session_state.token

try:
    dishes, token = get_dishes_with_relogin(token, date_str, meal_id)
except Exception as e:
    st.warning(f"메뉴를 불러오지 못했습니다: {e}")
    dishes = []

if not dishes:
    st.info("해당 날짜에 메뉴가 없습니다.")
else:
    all_courses = group_into_courses(dishes)
    takein = [g for g in all_courses if not is_takeout(g)]
    takeout = [g for g in all_courses if is_takeout(g)]

    for course in takein:
        render_course(course, date_str, meal_id, token)

    if takeout:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(f"🥡 포장 메뉴 ({len(takeout)}개)"):
            for course in takeout:
                name = main_dish_name(course)
                label = course_label(course)
                kcal = parse_kcal(course[0].get("sumKcal"))
                dish_names = [d["menuName"] for d in course]
                render_dish_table(label, name, dish_names)
                if kcal:
                    st.caption(f"🔥 {kcal} kcal")
                st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

# ── 방문자 카운터 ─────────────────────────────────────────────────────────────

visitor_today, visitor_total = fetch_visitor_counts()
today_disp = str(visitor_today) if visitor_today >= 0 else "--"
total_disp = str(visitor_total) if visitor_total >= 0 else "--"
st.markdown(
    f"<div style='text-align:center;color:var(--wm-footer);font-size:12px;margin-top:24px;'>"
    f"📧 rogermostwanted@gmail.com &nbsp;|&nbsp; Today {today_disp} &nbsp;Total {total_disp}"
    f"</div>",
    unsafe_allow_html=True,
)
