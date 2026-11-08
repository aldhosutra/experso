# Cost and time estimates

Reference run: 274 Instagram posts (185 reels, 89 carousels), Apple M1, Claude plan.

| Step | Time and cost |
|---|---|
| Download | 1.8 GB |
| Transcription | about 10 s per 1-minute reel, about 50 min in total |
| Extraction | about $0.31 per post API-equivalent on Opus, about 11 insights per post; 55–65 posts per Claude usage window |
| Grouping | about 5 min |
| Plan | about 4 min |
| Digest | about 1.5 Claude usage windows on Opus |
| Writing | about 5 min for 15 skills on Sonnet |
| **Total** | **about 4–5 Claude usage windows** |

Extraction and digest dominate, so cost scales roughly with the number of posts. A faster model for extraction (`--model sonnet`) costs about a third as much per post.
