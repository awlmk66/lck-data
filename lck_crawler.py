import requests
import json
import os
import time
from datetime import datetime, timedelta # [수정] timedelta 추가
from github import Github, Auth
def update_lck_safe():
    save_path = "lck_schedule.json"
    
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
                                # --- [수정 후] 한국 시간(KST) 보정 적용 ---
                ts = item.get('startTime') or item.get('startDate')
                if isinstance(ts, int):
                    # utcfromtimestamp를 사용하고 9시간을 더해 한국 시간으로 바꿉니다.
                    dt = datetime.utcfromtimestamp(ts / 1000) + timedelta(hours=9)
                    date_val = dt.strftime("%Y.%m.%d")
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
    access_token = os.getenv("GITHUB_TOKEN")
    if not access_token:
        access_token = "ghp_기존토큰"
    g = Github(access_token)
    
    repo = g.get_user().get_repo("lck-data") 
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # [수정] 입력받은 file_path에서 파일명만 추출하여 사용
    file_name = os.path.basename(file_path) 
    
    try:
        contents = repo.get_contents(file_name)
        repo.update_file(contents.path, f"{file_name} 자동 업데이트", content, contents.sha)
        print(f"🚀 GitHub {file_name} 업데이트 완료!")
    except Exception as e:
        repo.create_file(file_name, f"{file_name} 최초 생성", content)
        print(f"🚀 GitHub {file_name} 생성 완료!")

def update_lck_rank():
    # 1. 사용자님이 찾으신 진짜 API 주소
    url = "https://esports-api.game.naver.com/service/v1/ranking/lck_2026/team"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://game.naver.com/esports/League_of_Legends/record/lck/team/lck_2026"
    }
    
    print(f"📡 데이터 추출 시작: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # 응답 데이터 로드
        data = response.json()
        
        # 주신 데이터를 보면 'content' 자체가 리스트([])입니다.
        records = data.get('content', [])
        
        if not records:
            print("❌ 데이터를 찾을 수 없습니다. 응답을 확인하세요.")
            return

        rank_list = []
        for item in records:
            team_info = item.get('team', {})
            add_info = item.get('addInfo', {})
            
            # 안드로이드 앱에서 사용할 데이터만 쏙쏙 골라 담기
            rank_list.append({
                "rank": str(item.get('rank', '-')),
                "name": team_info.get('name', 'Unknown'),
                "win": str(item.get('wins', '0')),
                "lose": str(item.get('loses', '0')),
                "diff": str(item.get('score', '0')),
                "winRate": f"{int(item.get('winRate', 0) * 100)}%",
                "kda": str(add_info.get('kda', '0.0')),
                "logo": team_info.get('imageUrl', '') # 나중에 로고 띄울 때 유용함
            })
        
        # lck_rank.json 파일로 저장
        with open('lck_rank.json', 'w', encoding='utf-8') as f:
            json.dump(rank_list, f, ensure_ascii=False, indent=4)
            
        print(f"✅ [대성공] {len(rank_list)}개 팀의 순위 데이터를 저장했습니다!")
        print(f"📂 경로: {os.path.abspath('lck_rank.json')}")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

def update_lck_players():
    # 실제 네이버 선수 정보 API 주소는 시즌별로 형식이 다를 수 있습니다.
    # 만약 아래 주소가 작동하지 않는다면 브라우저 네트워크 탭에서 실제 주소를 확인해야 합니다.
    url = "https://esports-api.game.naver.com/service/v1/ranking/lck_2026/player" # 선수 순위/스탯 API
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://game.naver.com/esports/"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        # [방어 코드] 응답이 비어있거나 에러인지 확인
        if not response.text.strip():
            print("❌ 선수 정보 에러: 서버 응답이 비어있습니다. (API 주소 확인 필요)")
            return

        data = response.json()
        raw_players = data.get('content', [])
        
        player_list = []
        for p in raw_players:
            # 네이버 선수 API 구조에 맞춰 필드명 수정 (예시)
            player_list.append({
                "name": p.get('nickname', p.get('name', 'Unknown')),
                "team": p.get('teamName', 'TBD'),
                "position": p.get('positionValue', 'All'),
                "kda": str(p.get('kda', '0.0')),
                "kill": str(p.get('killCount', '0')),
                "death": str(p.get('deathCount', '0')),
                "assist": str(p.get('assistCount', '0'))
            })
        player_list.append({
            "name": "TEST_PLAYER",
            "team": "GEN",
            "position": "MID",
            "kda": "99.9",
            "kill": "100",
            "death": "0",
            "assist": "100"
        })
            
        with open('lck_players.json', 'w', encoding='utf-8') as f:
            json.dump(player_list, f, ensure_ascii=False, indent=4)
        print(f"✅ 선수 정보 저장 완료! ({len(player_list)}명)")

    except Exception as e:
        print(f"❌ 선수 정보 에러: {e}")

def upload_to_github(file_path):
    access_token = os.getenv("GITHUB_TOKEN") or "ghp_실제토큰값"
    
    # [수정] 최신 방식의 Auth 적용 (경고 메시지 해결)
    auth = Auth.Token(access_token)
    g = Github(auth=auth)
    
    repo = g.get_user().get_repo("lck-data") 
    file_name = os.path.basename(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    try:
        contents = repo.get_contents(file_name)
        repo.update_file(contents.path, f"{file_name} 자동 업데이트", content, contents.sha)
        print(f"🚀 GitHub {file_name} 업데이트 완료!")
    except Exception:
        repo.create_file(file_name, f"{file_name} 최초 생성", content)
        print(f"🚀 GitHub {file_name} 생성 완료!")

    
# --- 기존 코드 마지막 부분 ---
if __name__ == "__main__":
    # 1. 크롤링 수행 (현재 위치에 lck_schedule.json 생성)
    update_lck_safe()
    update_lck_rank()
    update_lck_players()
    # [수정] GITHUB_TOKEN이 없을 때(내 PC)만 직접 업로드 호출
    # GitHub 서버(Actions)에서는 YAML 설정으로 자동 업로드할 것이므로 중복 호출 방지
    if not os.getenv("GITHUB_ACTIONS"):
        # 경기 일정, 순위, 선수 정보 서버로 업로드 
        for file in ["lck_schedule.json", "lck_rank.json", "lck_players.json"]:
            upload_to_github(file)
