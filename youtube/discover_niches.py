"""
Ищем ниши, где молодые каналы (мало времени на рынке, невысокие обычные
просмотры) неожиданно выстреливают одним роликом в разы выше своей нормы.

Логика:
1. По каждой нише ищем топ-видео за последний год (сортировка по просмотрам).
2. Для канала каждого такого видео смотрим: возраст канала, подписчиков,
   и "обычные" просмотры (медиана последних видео на канале, кроме самого хита).
3. Если канал молодой, не гигант, и это видео сильно (в разы) выше его нормы —
   это "выстрел". Считаем такие выстрелы по каждой нише.
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API_KEY = open('.env').read().split('=', 1)[1].strip()
BASE = 'https://www.googleapis.com/youtube/v3'

CHANNEL_MAX_AGE_MONTHS = 15
CHANNEL_MAX_SUBS = 150_000
MIN_BREAKOUT_VIEWS = 100_000
OUTLIER_RATIO = 8
MIN_DURATION_SEC = 180  # отсекаем Shorts

NICHES = {
    "Бизнес-крахи / истории компаний": [
        "почему обанкротилась компания история",
        "крах бизнеса история компании",
    ],
    "Биографии и истории успеха": [
        "как разбогател история предпринимателя",
        "биография история жизни документальный",
    ],
    "Тайны и загадки истории": [
        "загадка истории документальный",
        "тайна которую скрывали история",
    ],
    "Реальные преступления (true crime)": [
        "реальное уголовное дело расследование",
        "громкое преступление история расследования",
    ],
    "Психология и разборы поведения": [
        "психология разбор личности документальный",
        "токсичное поведение разбор психолога",
    ],
    "Деньги и большие состояния": [
        "как заработал миллионы история",
        "история больших денег документальный",
    ],
    "Наука и технологии": [
        "научная тайна документальный",
        "технология изменившая мир история",
    ],
}


def api_get(endpoint, **params):
    params['key'] = API_KEY
    url = f"{BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def iso_duration_to_sec(d):
    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', d)
    if not m:
        return 0
    days, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s


def search_top_videos(query, published_after, max_results=15):
    data = api_get(
        'search', part='snippet', q=query, type='video', order='viewCount',
        publishedAfter=published_after, relevanceLanguage='ru', regionCode='RU',
        maxResults=max_results,
    )
    return [(it['id']['videoId'], it['snippet']['channelId'], it['snippet']['title'])
            for it in data.get('items', [])]


def get_videos_info(video_ids):
    out = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        data = api_get('videos', part='statistics,contentDetails', id=','.join(chunk))
        for it in data.get('items', []):
            out[it['id']] = {
                'views': int(it['statistics'].get('viewCount', 0)),
                'duration_sec': iso_duration_to_sec(it['contentDetails']['duration']),
            }
    return out


def get_channels_info(channel_ids):
    out = {}
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i + 50]
        data = api_get('channels', part='snippet,statistics,contentDetails', id=','.join(chunk))
        for it in data.get('items', []):
            out[it['id']] = {
                'title': it['snippet']['title'],
                'published_at': it['snippet']['publishedAt'],
                'subs': int(it['statistics'].get('subscriberCount', 0)),
                'uploads_playlist': it['contentDetails']['relatedPlaylists']['uploads'],
            }
    return out


def get_recent_views(uploads_playlist_id, exclude_video_id, limit=15):
    data = api_get('playlistItems', part='contentDetails', playlistId=uploads_playlist_id, maxResults=limit)
    ids = [it['contentDetails']['videoId'] for it in data.get('items', [])
           if it['contentDetails']['videoId'] != exclude_video_id]
    if not ids:
        return []
    infos = get_videos_info(ids)
    return [v['views'] for v in infos.values() if v['duration_sec'] >= MIN_DURATION_SEC]


def median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def main():
    now = datetime.now(timezone.utc)
    published_after = (now - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')

    results = {}
    seen_channels = set()

    for niche, queries in NICHES.items():
        results[niche] = []
        candidates = []
        for q in queries:
            candidates += search_top_videos(q, published_after)

        video_ids = [v[0] for v in candidates]
        vinfo = get_videos_info(video_ids)

        channel_ids = list({v[1] for v in candidates})
        cinfo = get_channels_info(channel_ids)

        for video_id, channel_id, title in candidates:
            if channel_id in seen_channels:
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

            seen_channels.add(channel_id)
            results[niche].append({
                'channel': c['title'],
                'age_months': round(age_months, 1),
                'subs': c['subs'],
                'typical_views': int(typical),
                'breakout_title': title,
                'breakout_views': v['views'],
                'ratio': round(v['views'] / typical, 1),
                'video_url': f"https://youtu.be/{video_id}",
            })

    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('done')


if __name__ == '__main__':
    main()
