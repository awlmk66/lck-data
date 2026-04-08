import requests
import json
import os
import time
from datetime import datetime, timedelta # [수정] timedelta 추가
from github import Github
def update_lck_safe():
    save_path = r"C:\Users\VIVO_book\AndroidStudioProjects\LCKSchedule2\app\src\main\assets\lck_schedule.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://game.naver.com/esports/schedule/lck"
    }

    all_raw_matches = []
    
    # [해결] now 변수를 루프 밖에서 먼저 정의합니다.
    now = datetime.now()

    # 이번 달(i=0)과 다음 달(i=1)을 가져오기 위한 루프
    for i in range(2):
        # [수정] 현재 날짜 기준으로 타겟 월 계산
        target_date = datetime(now.year, now.month, 1) + timedelta(days=i*31)
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

                # 시간 및 날짜 파싱
                ts = item.get('startTime') or item.get('startDate')
                if isinstance(ts, int):
                    dt = datetime.fromtimestamp(ts / 1000)
                    date_val = dt.strftime("%Y.%m.%d")
                    time_val = dt.strftime("%H:%M")
                else:
                    raw_start = str(item.get('startDate', ""))
                    date_val = raw_start[:10].replace("-", ".")
                    time_val = raw_start[11:16] if len(raw_start) > 16 else "00:00"

                all_raw_matches.append({
                    "date": date_val,
                    "time": time_val,
                    "home": convert_team(home_name.lower()),
                    "away": convert_team(away_name.lower())
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
    # GitHub Actions 환경에서 GH_TOKEN을 가져옵니다.
    access_token = os.getenv("GH_TOKEN") 
    
    if not access_token:
        # 만약 로컬 PC에서 테스트할 때를 위해 기존 토큰을 남겨둘 수도 있습니다.
        access_token = "ghp_기존_토큰_값"
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
    update_lck_safe()
    # 크롤링이 끝난 후 저장된 파일을 GitHub로 업로드!
    save_path = r"C:\Users\VIVO_book\AndroidStudioProjects\LCKSchedule2\app\src\main\assets\lck_schedule.json"
    upload_to_github(save_path)
