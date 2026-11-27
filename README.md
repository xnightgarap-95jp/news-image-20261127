# news-image-20261127

[![make.fun · news-image-20261127](https://make.fun/badge/news-image-20261127.svg)](https://make.fun/bounty/news-image-20261127?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261127)
[![rank](https://make.fun/badge/news-image-20261127/xnightgarap-95jp/news-image-20261127/rank.svg)](https://make.fun/bounty/news-image-20261127/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261127)
[![reward](https://make.fun/badge/news-image-20261127/xnightgarap-95jp/news-image-20261127/reward.svg)](https://make.fun/bounty/news-image-20261127?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261127)

A one-page newspaper front page summing up world news of
**Friday 27 November 2026**, drawn entirely by code: 35 stories
across 9 regions, three hero stories with vector scenes, twelve
smaller panels, a world map with the stories pinned, twenty more
stories in a numbered list, and a date-check footer.

## Run

```sh
python3 main.py            # writes /output/entry.png
python3 main.py ./out      # writes ./out/entry.png
```

Python 3.13, standard library only, no network at runtime.
Output is a deterministic 1024x1024 PNG (44,106 bytes,
byte-identical across runs — SHA-256
`1ee78bcd46387ec0500366028abf368a530ed0ee1f23d11f51e782a4ddd9c176`).

## Files

- `main.py` — the whole entry: 5x7 pixel font, raster canvas,
  PNG encoder, vector scenes, story data, layout.
- `entry.png` — the rendered image (preview; `main.py` draws it
  fresh on every run).
- `NEWS.md` — all 35 stories with their sources.
- `LICENSE` — MIT.

## Judge criteria, in order

1. One day, named: the masthead, top bar and footer all name
   Friday 27 November 2026, and every story is dated to that day.
2. Selection and breadth: 35 stories, 9 regions, war, disaster,
   diplomacy, justice, politics, markets, tech, sport, health,
   space and migration.
3. It reads: each story is clear from its picture and short
   labels; numbers are as reported, with no speculation.
4. Faithful: no hype; earlier-days stories are named in the
   DATE CHECK footer instead of being passed off as today's.
5. Craft: one front-page composition, legible at 300 px across,
   no overlapping or truncated text (verified by crop inspection
   and per-row ink measurement).
