import requests
import json
import os
import time
from datetime import datetime, timedelta # [수정] timedelta 추가
from github import Github, Auth
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

import os
from github import Github, Auth # Auth를 추가로 임포트하세요

def upload_to_github(file_path):
    # 1. 환경 변수에서 토큰 가져오기
    token = os.getenv("GH_TOKEN")
    
    if not token:
        print("❌ 에러: GH_TOKEN 환경 변수를 찾을 수 없습니다.")
        return

    try:
        # 2. 최신 권장 방식(Auth)으로 인증 객체 생성
        auth = Auth.Token(token)
        g = Github(auth=auth)

        # 3. 내 리포지토리 불러오기
        # '아이디/리포지토리이름' 형식으로 직접 입력하는 것이 가장 안전합니다.
        # 예: "mygithub-id/lck-data"
        repo = g.get_repo("awlmk66/lck-data") 

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        file_name = "lck_schedule.json"

        # 4. 파일 업데이트 또는 생성
        try:
            contents = repo.get_contents(file_name)
            repo.update_file(contents.path, "자동 일정 업데이트", content, contents.sha)
            print("🚀 GitHub 업데이트 완료!")
        except:
            repo.create_file(file_name, "최초 일정 생성", content)
            print("🚀 GitHub 파일 생성 완료!")
            
    except Exception as e:
        print(f"❌ GitHub 작업 중 상세 에러 발생: {e}")

# ... 하단 실행부 ...
if __name__ == "__main__":
    # 1. 크롤링 함수를 실행하고 결과 경로를 받아옵니다. 
    # (함수 이름이 update_lck_safe()가 맞는지 확인하세요!)
    try:
        current_path = update_lck_safe() 
        
        # 2. 업로드 함수 호출
        # 방금 만든 'current_path' 변수를 그대로 전달합니다.
        upload_to_github(current_path)
        
    except NameError:
        # 혹시 위에서 변수명이 꼬였을 경우를 대비한 안전장치
        # 파일이 현재 폴더에 "lck_schedule.json" 이름으로 저장된다면 아래처럼 직접 적어도 됩니다.
        upload_to_github("lck_schedule.json")
    except Exception as e:
        print(f"❌ 실행 중 에러 발생: {e}")
