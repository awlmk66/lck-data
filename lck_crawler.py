import requests
import json
import os
import time
from datetime import datetime, timedelta, timezone# [수정] timedelta 추가
from github import Github
def update_lck_safe():
    save_path = "lck_schedule.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://game.naver.com/esports/schedule/lck"
    }

    all_raw_matches = []

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)

    # 이번 달(i=0)과 다음 달(i=1)을 가져오기 위한 루프
    for i in range(2):
        # [수정] 현재 날짜 기준으로 타겟 월 계산
        target_date = datetime(now.year, now.month, 1, tzinfo=kst) + timedelta(days=i*31)
        target_month_str = target_date.strftime("%Y-%m")
        
        print(f"📅 작업 대상 월: {target_month_str}")

        # API 주소에 동적으로 생성된 월 문자열 삽입
        url = f"https://esports-api.game.naver.com/service/v2/schedule/month?month={target_month_str}&topLeagueId=lck&relay=false"
        
        try:
            print(f"📡 요청 URL: {url}")
            response = requests.get(url, headers=headers)
            data = response.json()
            
            # v2 API 구조: content -> matches
            content_data = data.get('content', {})
            matches = content_data.get('matches', []) if isinstance(content_data, dict) else []
            
            if not matches:
                print(f"ℹ️ {target_month_str}월: 데이터가 비어있습니다.")
                continue

            for item in matches:
                home_obj = item.get('homeTeam') or {}
                away_obj = item.get('awayTeam') or {}
                
                home_name = home_obj.get('nameEngAcronym')
                away_name = away_obj.get('nameEngAcronym')

                if not home_name or not away_name:
                    continue
                
                # --- [수정 시작] 점수 데이터 가져오기 ---
                # 네이버 API는 homeScore, awayScore 필드를 제공합니다.
                # 경기가 아직 안 열렸을 경우를 대비해 기본값 ""을 설정합니다.
                h_score_raw = item.get('homeScore') if item.get('homeScore') is not None else 0
                a_score_raw = item.get('awayScore') if item.get('awayScore') is not None else 0
                if h_score_raw == 0 and a_score_raw == 0:
                    home_score = "-"
                    away_score = "-"
                else:
                    home_score = str(h_score_raw)
                    away_score = str(a_score_raw)
                # --- [수정 끝] ---

                # 시간 및 날짜 파싱 (기존 로직 동일)
                ts = item.get('startTime') or item.get('startDate')
                if isinstance(ts, int):
                    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone(kst)
    
                    # 요일 리스트 생성 및 추출
                    days = ['월', '화', '수', '목', '금', '토', '일']
                    weekday = days[dt.weekday()]
                    
                    # 날짜 뒤에 요일 추가 (%Y.%m.%d (%a) 형식)
                    date_val = dt.strftime(f"%Y.%m.%d ({weekday})")
                    time_val = dt.strftime("%H:%M")
                else:
                    raw_start = str(item.get('startDate', ""))
                    date_val = raw_start[:10].replace("-", ".")
                    time_val = raw_start[11:16] if len(raw_start) > 16 else "00:00"

                # [수정] 딕셔너리에 점수 추가
                all_raw_matches.append({
                    "date": date_val,
                    "time": time_val,
                    "home": convert_team(home_name.lower()),
                    "away": convert_team(away_name.lower()),
                    "homeScore": home_score, # 추가된 부분
                    "awayScore": away_score  # 추가된 부분
                })
            
            time.sleep(0.3)

        except Exception as e:
            print(f"❌ {target_month_str} 에러: {e}")

    # 중복 제거 및 정렬
    unique_matches = []
    seen = set()
    for m in all_raw_matches:
        identifier = (m['date'], m['time'], m['home'], m['away'])
        if identifier not in seen:
            unique_matches.append(m)
            seen.add(identifier)
    unique_matches.sort(key=lambda x: (x['date'], x['time']))

    # 파일 저장
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(unique_matches, f, ensure_ascii=False, indent=4)
    print(f"🏁 저장 완료! 총 {len(unique_matches)}개 경기 (2개월 분량)")

def convert_team(name):
    if name in ["bfx", "fox", "bnk", "fearx"]: return "bnk"
    if name in ["bro", "brion"]: return "bro"
    if name in ["gen", "geng"] : return "gen"
    if name in ["krx", "drx"] : return "drx"
    return name

def upload_to_github(file_path):
    # 1. 아까 복사해둔 ghp_... 토큰을 입력하세요
    access_token = os.getenv("GITHUB_TOKEN")
    if not access_token:
        access_token = "ghp_기존토큰"
    g = Github(access_token)
    
    # 2. 본인의 "GitHub아이디/리포지토리이름"을 적으세요 (예: "user123/lck-data")
    repo = g.get_user().get_repo("lck-data") 
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    file_name = "lck_schedule.json" # 저장소에 올라갈 파일 이름
    
    try:
        # 기존 파일이 있는지 확인 (있다면 덮어쓰기 위해 sha 값이 필요함)
        contents = repo.get_contents(file_name)
        repo.update_file(contents.path, "LCK 일정 자동 업데이트", content, contents.sha)
        print("🚀 GitHub 업데이트 완료!")
    except Exception as e:
        # 파일이 없다면 새로 생성
        repo.create_file(file_name, "LCK 일정 최초 생성", content)
        print("🚀 GitHub 파일 생성 완료!")

# --- 기존 코드 마지막 부분 ---
if __name__ == "__main__":
    # 1. 크롤링 수행 (현재 위치에 lck_schedule.json 생성)
    update_lck_safe()
    
    # [수정] GITHUB_TOKEN이 없을 때(내 PC)만 직접 업로드 호출
    # GitHub 서버(Actions)에서는 YAML 설정으로 자동 업로드할 것이므로 중복 호출 방지
    if not os.getenv("GITHUB_ACTIONS"): 
        save_path = "lck_schedule.json"
        upload_to_github(save_path)
