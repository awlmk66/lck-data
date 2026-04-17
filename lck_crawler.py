import requests
import json
import os
import time
from datetime import datetime, timedelta
from github import Github, Auth

# --- [유틸리티] 팀 이름 변환 ---
def convert_team(name):
    if not name: return "tbd"
    name = name.lower()
    if name in ["bfx", "fox", "bnk", "fearx"]: return "bnk"
    if name in ["bro", "brion"]: return "bro"
    if name in ["gen", "geng"] : return "gen"
    if name in ["krx", "drx"] : return "drx"
    return name

# --- [1] 경기 일정 업데이트 ---
def update_lck_safe():
    save_path = "lck_schedule.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://game.naver.com/esports/schedule/lck"
    }

    all_raw_matches = []
    now = datetime.now()

    for i in range(2):
        target_date = datetime(now.year, now.month, 1) + timedelta(days=i*31)
        target_month_str = target_date.strftime("%Y-%m") 
        url = f"https://esports-api.game.naver.com/service/v2/schedule/month?month={target_month_str}&topLeagueId=lck&relay=false"
        
        try:
            print(f"📅 작업 대상 월: {target_month_str} (일정)")
            response = requests.get(url, headers=headers)
            data = response.json()
            content_data = data.get('content', {})
            matches = content_data.get('matches', []) if isinstance(content_data, dict) else []
            
            for item in matches:
                home_obj = item.get('homeTeam') or {}
                away_obj = item.get('awayTeam') or {}
                home_name = home_obj.get('nameEngAcronym')
                away_name = away_obj.get('nameEngAcronym')

                if not home_name or not away_name: continue
                
                h_score_raw = item.get('homeScore')
                a_score_raw = item.get('awayScore')
                if h_score_raw is None or a_score_raw is None:
                    home_score, away_score = "-", "-"
                else:
                    home_score, away_score = str(h_score_raw), str(a_score_raw)

                ts = item.get('startTime') or item.get('startDate')
                if isinstance(ts, int):
                    dt = datetime.utcfromtimestamp(ts / 1000) + timedelta(hours=9)
                    date_val, time_val = dt.strftime("%Y.%m.%d"), dt.strftime("%H:%M")
                else:
                    raw_start = str(item.get('startDate', ""))
                    date_val = raw_start[:10].replace("-", ".")
                    time_val = raw_start[11:16] if len(raw_start) > 16 else "00:00"

                all_raw_matches.append({
                    "date": date_val, "time": time_val,
                    "home": convert_team(home_name), "away": convert_team(away_name),
                    "homeScore": home_score, "awayScore": away_score
                })
            time.sleep(0.3)
        except Exception as e:
            print(f"❌ {target_month_str} 일정 에러: {e}")

    unique_matches = []
    seen = set()
    for m in all_raw_matches:
        identifier = (m['date'], m['time'], m['home'], m['away'])
        if identifier not in seen:
            unique_matches.append(m)
            seen.add(identifier)
    unique_matches.sort(key=lambda x: (x['date'], x['time']))

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(unique_matches, f, ensure_ascii=False, indent=4)
    print(f"🏁 일정 저장 완료! ({len(unique_matches)}개)")

# --- [2] 팀 순위 업데이트 ---
def update_lck_rank():
    url = "https://esports-api.game.naver.com/service/v1/ranking/lck_2026/team"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://game.naver.com/esports/"}
    
    try:
        response = requests.get(url, headers=headers)
        records = response.json().get('content', [])
        rank_list = []
        for item in records:
            team_info = item.get('team', {})
            rank_list.append({
                "rank": str(item.get('rank', '-')),
                "name": team_info.get('name', 'Unknown'),
                "win": str(item.get('wins', '0')),
                "lose": str(item.get('loses', '0')),
                "diff": str(item.get('score', '0')),
                "winRate": f"{int(item.get('winRate', 0) * 100)}%",
                "kda": str(item.get('addInfo', {}).get('kda', '0.0')),
                "logo": team_info.get('imageUrl', '')
            })
        with open('lck_rank.json', 'w', encoding='utf-8') as f:
            json.dump(rank_list, f, ensure_ascii=False, indent=4)
        print(f"✅ 순위 저장 완료! ({len(rank_list)}개 팀)")
    except Exception as e:
        print(f"❌ 순위 에러: {e}")

# --- [3] 선수 정보 업데이트 (수정 핵심 부분) ---
def update_lck_players():
    url = "https://esports-api.game.naver.com/service/v1/ranking/lck_2026/player"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://game.naver.com/esports/"}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        records = data.get('content', [])
        
        player_list = [] # 리스트 초기화 정의
        
        for item in records:
            p_info = item.get('player', {})
            t_info = item.get('team', {})
            
            # 실제 네이버 구조 반영: nickName (대문자 N)
            name = p_info.get('nickName') or p_info.get('name') or "Unknown"
            team = t_info.get('name') or "TBD"
            
            player_list.append({
                "name": name,
                "team": team,
                "position": item.get('positionValue', 'All'),
                "kda": str(item.get('kda', '0.0')),
                "kill": str(item.get('wins', '0')), # 세부 스탯은 API 구조에 맞춰 wins/loses 활용
                "death": str(item.get('loses', '0')),
                "assist": str(item.get('score', '0')),
                "imageUrl": p_info.get('imageUrl', '')
            })
            
            
        with open('lck_players.json', 'w', encoding='utf-8') as f:
            json.dump(player_list, f, ensure_ascii=False, indent=4)
        print(f"✅ 선수 정보 저장 완료! ({len(player_list)}명)")

    except Exception as e:
        print(f"❌ 선수 정보 에러: {e}")

# --- [4] GitHub 업로드 ---
def upload_to_github(file_path):
    # 환경변수가 없으면 수동 입력된 토큰 사용
    token = os.getenv("GITHUB_TOKEN") or "ghp_기존토큰"
    
    # 최신 PyGithub 인증 방식 (Auth.Token 사용)
    auth = Auth.Token(token)
    g = Github(auth=auth)
    
    try:
        repo = g.get_user().get_repo("lck-data") 
        file_name = os.path.basename(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        try:
            contents = repo.get_contents(file_name)
            repo.update_file(contents.path, f"{file_name} 업데이트", content, contents.sha)
            print(f"🚀 GitHub {file_name} 업데이트 완료!")
        except:
            repo.create_file(file_name, f"{file_name} 생성", content)
            print(f"🚀 GitHub {file_name} 생성 완료!")
    except Exception as e:
        print(f"❌ GitHub 업로드 실패 ({file_path}): {e}")

# --- 메인 실행부 ---
if __name__ == "__main__":
    update_lck_safe()     # 일정
    update_lck_rank()     # 순위
    update_lck_players()  # 선수 (이제 Unknown 안 뜸!)

    # 로컬 환경에서만 실행 (GitHub Actions 중복 방지)
    if not os.getenv("GITHUB_ACTIONS"):
        for file in ["lck_schedule.json", "lck_rank.json", "lck_players.json"]:
            if os.path.exists(file):
                upload_to_github(file)
