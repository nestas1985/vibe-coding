"""
Разбор ниш из файла "подбор ниш.txt":
1. Смотрим конкретные каналы, которые дал Стас — их возраст, подписчики,
   "обычные" просмотры и лучший ролик (собственный ratio выстрела канала).
2. Отдельно ищем более широкий круг конкурентов по каждой нише (не
   ограничиваясь только этими каналами) — тем же методом, что и раньше.
"""
import json
import re
from datetime import datetime, timedelta, timezone

from discover_niches import (
    api_get, search_top_videos, get_videos_info, get_channels_info, get_recent_views, median,
    CHANNEL_MAX_AGE_MONTHS, CHANNEL_MAX_SUBS, MIN_BREAKOUT_VIEWS, OUTLIER_RATIO, MIN_DURATION_SEC,
)

FILE_PATH = 'подбор ниш.txt'

SEARCH_QUERIES = {
    "тайные места": ["тайное место документальный", "загадочное место которое скрывали"],
    "психология, отношения, мотивация": ["психология отношений документальный", "мотивационная история человека"],
    "история, средневековье": ["средневековье история документальный", "тайна средних веков"],
    "истории компаний и брендов": ["история бренда документальный", "как создали компанию история"],
    "истории про пиратов": ["пираты история документальный", "золото пиратов история"],
    "истории про банды": ["банда история документальный", "преступная группировка история"],
    "истории про известные личности": ["известная личность история документальный", "судьба знаменитого человека"],
}


def parse_file(path):
    niches = {}
    current = None
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('http'):
            m = re.search(r'@([\w\-]+)', line)
            if current and m:
                niches.setdefault(current, []).append(m.group(1))
        else:
            current = line
    return niches


def resolve_channel(handle):
    try:
        data = api_get('channels', part='snippet,statistics,contentDetails', forHandle=handle)
    except Exception as e:
        return {'handle': handle, 'error': str(e)}
    items = data.get('items', [])
    if not items:
        return {'handle': handle, 'error': 'not found'}
    it = items[0]
    return {
        'handle': handle,
        'title': it['snippet']['title'],
        'published_at': it['snippet']['publishedAt'],
        'subs': int(it['statistics'].get('subscriberCount', 0)),
        'video_count': int(it['statistics'].get('videoCount', 0)),
        'uploads_playlist': it['contentDetails']['relatedPlaylists']['uploads'],
    }


def channel_own_breakout(channel, now):
    if 'error' in channel:
        return channel
    age_months = (now - datetime.fromisoformat(channel['published_at'].replace('Z', '+00:00'))).days / 30
    try:
        recent = get_recent_views(channel['uploads_playlist'], exclude_video_id='', limit=30)
    except Exception as e:
        return {**channel, 'age_months': round(age_months, 1), 'error': f'no videos / {e}'}
    if not recent:
        typical = 0
        breakout = 0
        ratio = 0
    else:
        breakout = max(recent)
        rest = [v for v in recent if v != breakout]
        typical = median(rest) if rest else breakout
        ratio = round(breakout / typical, 1) if typical else 0
    return {
        **channel,
        'age_months': round(age_months, 1),
        'typical_views': int(typical),
        'best_video_views': breakout,
        'own_ratio': ratio,
    }


def find_competitors(queries, now, published_after, exclude_channel_ids):
    found = []
    candidates = []
    for q in queries:
        candidates += search_top_videos(q, published_after, max_results=20)

    video_ids = [v[0] for v in candidates]
    vinfo = get_videos_info(video_ids)
    channel_ids = list({v[1] for v in candidates})
    cinfo = get_channels_info(channel_ids)

    seen = set()
    for video_id, channel_id, title in candidates:
        if channel_id in seen or channel_id in exclude_channel_ids:
            continue
        v = vinfo.get(video_id)
        c = cinfo.get(channel_id)
        if not v or not c:
            continue
        if v['duration_sec'] < MIN_DURATION_SEC or v['views'] < MIN_BREAKOUT_VIEWS:
            continue
        if c['subs'] > CHANNEL_MAX_SUBS:
            continue
        age_months = (now - datetime.fromisoformat(c['published_at'].replace('Z', '+00:00'))).days / 30
        if age_months > CHANNEL_MAX_AGE_MONTHS:
            continue
        recent = get_recent_views(c['uploads_playlist'], video_id)
        typical = median(recent)
        if typical == 0 or v['views'] / typical < OUTLIER_RATIO:
            continue
        seen.add(channel_id)
        found.append({
            'channel': c['title'],
            'age_months': round(age_months, 1),
            'subs': c['subs'],
            'typical_views': int(typical),
            'breakout_title': title,
            'breakout_views': v['views'],
            'ratio': round(v['views'] / typical, 1),
            'video_url': f"https://youtu.be/{video_id}",
        })
    return found


def main():
    now = datetime.now(timezone.utc)
    published_after = (now - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')

    file_niches = parse_file(FILE_PATH)
    result = {}

    for niche, handles in file_niches.items():
        listed_channels = []
        exclude_ids = set()
        for h in handles:
            ch = resolve_channel(h)
            if 'error' not in ch:
                exclude_ids.add(api_get('channels', part='id', forHandle=h)['items'][0]['id'])
                ch = channel_own_breakout(ch, now)
            listed_channels.append(ch)

        competitors = find_competitors(SEARCH_QUERIES.get(niche, []), now, published_after, exclude_ids)

        result[niche] = {
            'listed_channels': listed_channels,
            'broader_competitors': competitors,
        }

    with open('file_niches_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print('done')


if __name__ == '__main__':
    main()
