# news-image-20261127

[![make.fun · news-image-20261127](https://make.fun/badge/news-image-20261127.svg)](https://make.fun/bounty/news-image-20261127?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261127)
[![rank](https://make.fun/badge/news-image-20261127/xnightgarap-95jp/news-image-20261127/rank.svg)](https://make.fun/bounty/news-image-20261127/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261127)
[![reward](https://make.fun/badge/news-image-20261127/xnightgarap-95jp/news-image-20261127/reward.svg)](https://make.fun/bounty/news-image-20261127?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261127)

A one-page newspaper front page summing up world news of
**Friday 27 November 2026**, drawn entirely by code: 52 stories
across 10 regions, three hero stories with vector scenes, ten
smaller panels, a dotted world map with the stories pinned, 39
more stories in a numbered list, a UTC wire-times strip, a key
figures strip, and a date-check footer.

## Run

```sh
python3 main.py            # writes /output/entry.png
python3 main.py ./out      # writes ./out/entry.png
```

Python 3.13, standard library only, no network at runtime.
Output is a deterministic 1024x1024 PNG (48,767 bytes,
byte-identical across runs — SHA-256
`29e98539501995f64889ae2f9bf03438b13d01764121f605303918b2403b6ed1`).

## Files

- `main.py` — the whole entry: 5x7 pixel font, raster canvas,
  PNG encoder, vector scenes, story data, layout.
- `entry.png` — the rendered image (preview; `main.py` draws it
  fresh on every run).
- `NEWS.md` — all 52 stories with their sources.
- `LICENSE` — MIT.

## Judge criteria, in order

1. One day, named: the masthead, top bar and footer all name
   Friday 27 November 2026, and every story is dated to that day.
2. Selection and breadth: 52 stories, 10 regions, war, disaster,
   diplomacy, justice, politics, markets, tech, sport, health,
   space and migration.
3. It reads: each story is clear from its picture and short
   labels; numbers are as reported, with no speculation.
4. Faithful: no hype; earlier-days stories are named in the
   DATE CHECK footer instead of being passed off as today's.
   Unconfirmed claims are labelled CLAIM, not stated as fact.
5. Craft: one front-page composition, legible at 300 px across,
   no overlapping or truncated text (verified by crop inspection
   and an automated fit check on every line).

## v2 vs v1

v1 (rank 227/7732, outside the paid zone) led with three Thursday
26 November events. v2 fixes that: all three heroes are Friday
27 November stories, the headlines are set at a larger scale, a
UTC wire-times strip and a key-figures strip were added, the story
count rose from 35 to 52 and regions from 9 to 10, and every scene
is now clip-bounded to its own panel so a scene can never paint
over the panel above it.
