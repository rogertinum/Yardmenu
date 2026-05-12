# 삼성중공업 식단 앱 (Welmenu)

삼성중공업 A식당(REST000076)의 아침/점심/저녁 식단을 확인하는 Streamlit 웹앱입니다.

## 기능

- 날짜 네비게이션 (오늘 / 이전날 / 다음날)
- 아침 / 점심 / 저녁 탭 전환
- 코스별 메뉴 목록 및 음식 사진 표시
- 칼로리(kcal) 표시
- 포장(테이크아웃) 메뉴 별도 구분

## 기술 스택

- **Frontend**: Streamlit
- **API**: Welstory(Welplus) 내부 REST API
- **인증**: username/password 로그인 → Authorization 토큰
- **배포**: Streamlit Cloud

## 개발 현황

| 항목 | 상태 |
|------|------|
| 로그인 및 토큰 관리 | ✅ 완료 |
| 날짜 네비게이션 UI | ✅ 완료 |
| 아침/점심/저녁 탭 | ✅ 완료 |
| 메뉴 목록 렌더링 | ✅ 완료 |
| 음식 사진 표시 | ✅ 완료 |
| 칼로리 표시 | ✅ 완료 |
| 포장 메뉴 분리 | ✅ 완료 |
| Streamlit Cloud 배포 | ✅ 완료 |

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```


## 만든 사람

- **rogertinum** — 기획 및 개발
- 개발 보조: Claude (Anthropic)
- 개발 기간: 2026년 5월
