"""
Углублённый разбор ниши "Тайны и загадки" — раскладываем по поднишам,
чтобы понять, какая конкретно поднишеа (история/наука/аномалии/сон и т.д.)
даёт больше всего "выстрелов" у молодых каналов.
"""
import json
from datetime import datetime, timedelta, timezone

from discover_niches import (
    search_top_videos, get_videos_info, get_channels_info, get_recent_views, median,
    CHANNEL_MAX_AGE_MONTHS, CHANNEL_MAX_SUBS, MIN_BREAKOUT_VIEWS, OUTLIER_RATIO, MIN_DURATION_SEC,
)

SUBNICHES = {
    "Тайны истории (общее)": [
        "тайна истории документальный",
        "загадка которую скрывали историки",
    ],
    "Тайны СССР / рассекречено": [
        "правда которую скрывали СССР",
        "рассекречено спустя годы документальный",
    ],
    "Древние цивилизации / археология": [
        "древняя цивилизация тайна документальный",
        "археологическая находка которая шокировала",
    ],
    "Природные аномалии / места": [
        "аномальное место документальный",
        "необъяснимое явление природы документальный",
    ],
    "Тайны космоса и вселенной": [
        "тайна вселенной документальный",
        "загадка космоса необъяснимо",
    ],
    "Контент 'для сна'": [
        "документальный фильм для сна",
        "лекция для сна тайны загадки",
    ],
    "Мистика / необъяснимые случаи": [
        "мистическая история документальный",
        "необъяснимый случай документальный",
    ],
    "Тайны океана и глубин": [
        "тайна океана документальный",
        "загадка морских глубин",
    ],
}


def main():
    now = datetime.now(timezone.utc)
    published_after = (now - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')

    results = {}
    seen_channels = set()

    for subniche, queries in SUBNICHES.items():
        results[subniche] = []
        candidates = []
        for q in queries:
            candidates += search_top_videos(q, published_after, max_results=20)

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
            results[subniche].append({
                'channel': c['title'],
                'age_months': round(age_months, 1),
                'subs': c['subs'],
                'typical_views': int(typical),
                'breakout_title': title,
                'breakout_views': v['views'],
                'ratio': round(v['views'] / typical, 1),
                'duration_min': round(v['duration_sec'] / 60, 1),
                'video_url': f"https://youtu.be/{video_id}",
            })

    with open('mysteries_deep.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('done')


if __name__ == '__main__':
    main()
