# LoopLearn — "Loop in" Feature: Build Tracker

Started as design notes from a planning conversation; now doubles as the
build tracker. **As of the last update, nothing described here had actually
been merged into this repo** — the ✅ marks below originally meant "designed"
rather than "in the codebase." Status markers are being corrected as pieces
actually land:

- ✅ **Built** — code exists in this repo and has been smoke-tested.
- 🚧 **Designed, not built** — spec below, no code yet.
- 💭 **Open** — still an undecided design question.

Building in small, complete chunks, one file/concern at a time.

---

## 1. The feature, in one paragraph

A user types **any topic** (not limited to LoopLearn's existing domain graph)
plus their **intent** — what specifically they want out of it, their current
level, their goal. The system runs a gap analysis (what their intent already
covers vs. what a working understanding actually requires), then produces
**two different artifacts** from the same research:

- A **blog article**, structured one section per subtopic, calling out the
  gaps explicitly rather than silently folding them in.
- A **two-host podcast script + audio**, covering the same subtopics but
  arrived at through genuine back-and-forth conversation — not a narration
  of the blog.

---

## 2. Pipeline, end to end

1. ✅ **Gap analysis** (`app/services/gap_analyzer.py`) — one LLM call on
   **Groq** (`openai/gpt-oss-120b`, `groq` SDK, `response_format:
   json_object`), not Gemini. Originally implemented the §4 hybrid idea
   (gap analysis on Groq, blog/podcast on Gemini); all three calls now run
   on Groq — see the all-Groq switch note under step 5. `tenacity` retry
   kept from the `topic_compiler.py` pattern. Input: topic + intent.
   Output: `{requested, gaps, recommended_scope}` — the subtopics the user
   already implied they want, the ones they're missing, and the full
   ordered list to actually research and write about. Input length is
   capped (`MAX_TOPIC_LENGTH=200`, `MAX_INTENT_LENGTH=1000`, raising
   `GapAnalysisInputError`) — folds in §6.6 early since it was trivial to
   add at the same time. `groq` added to `requirements.txt`. Smoke-tested
   twice against the real Groq API (once before, once after the Gemini→
   Groq swap) with a Kubernetes topic/intent pair; both returned a valid,
   sensibly ordered schema.
2. ✅ **Source gathering** (`app/services/loop_in_source_service.py`) — for
   each subtopic in `recommended_scope`, reuses the existing `fetcher.py`
   (DuckDuckGo) + `scraper.py` (trafilatura). Fetches candidate URLs per
   subtopic, then scrapes **round-robin across subtopics** (not
   subtopic-by-subtopic) so an early subtopic can't eat the whole source
   budget — capped at `MAX_SOURCES=6` successfully-scraped sources total,
   with a `MAX_SCRAPE_ATTEMPTS=20` safety ceiling on wasted attempts.
   Deliberately does **not** call `text_cleaner.clean_text` — smoke-testing
   found that function currently returns `''` for any input (it iterates
   `text.strip("\n")` character-by-character instead of splitting into
   lines, at `app/services/text_cleaner.py:29`, so every line is under the
   30-char keep threshold). That's a pre-existing bug shared with the daily
   pipeline, out of scope for Loop in to fix, but worth knowing it's
   silently degrading source quality there too. Smoke-tested against real
   DDG search + live scraping across 4 Kubernetes subtopics: hit the
   6-source cap with round-robin coverage across 3 of the 4 subtopics.
3. ✅ **Blog compile** (`app/services/blog_compiler.py`) — one LLM call, now
   on **Groq** (`openai/gpt-oss-120b`). Originally built on Gemini 2.5 Flash
   per the §4 hybrid split; moved to Groq on explicit direction to keep
   Loop in entirely off Gemini (see the all-Groq switch note at the end of
   this section). Produces exactly one section per `recommended_scope`
   entry, in the same order — validated in code (section count + subtopic
   match), not just trusted from the prompt, raising (and retrying via
   `tenacity`) on mismatch. `is_gap` is computed in code from the gap
   analysis rather than trusted from the LLM, and gap sections are
   instructed to explicitly call out *why* they're included, per §1's
   "calling out the gaps explicitly" requirement. Each section may include
   a Mermaid diagram only where it genuinely helps (escaping rules carried
   over from `topic_compiler.py`, and still matter now that diagrams render
   client-side — see step 4). Smoke-tested end-to-end (gap analysis →
   source gathering → blog compile) on a real Kubernetes topic, both on
   Gemini and again after the Groq switch: correct section count/order,
   gaps correctly flagged, some sections chose to include a diagram.
4. ❌ **Server-side diagram rendering — built, then reverted, approach
   changed.** Originally built `app/services/diagram_render_service.py`:
   base64-encode each section's Mermaid code, fetch a PNG from
   `mermaid.ink`, upload to Cloudinary, replace `mermaid` with
   `diagram_image_url`. Smoke-tested and working end-to-end (4 of 6
   sections rendered correctly), but the first render was visually
   inspected and looked bad — mermaid.ink's default theme (pastel
   yellow/purple, cramped layout). Fixed that
   (`theme=neutral&width=1200&scale=2&bgColor=white`, mermaid.ink also
   rejects `scale` unless `width`/`height` is set — found via a live 400)
   and the re-rendered output looked clean.

   **Then the approach itself was dropped.** Decision: render Mermaid
   **client-side in the frontend** with the
   [`mermaid`](https://www.npmjs.com/package/mermaid) npm package instead
   of server-side PNG generation. `diagram_render_service.py` deleted —
   nothing else depended on it yet (orchestrator/step 7 isn't built), so
   no dependents to clean up. This means:
   - `blog_compiler.py` (§2 step 3) needs **no change** — its
     `mermaid: {"diagram_type", "code"}` per section is already exactly
     the shape a frontend `mermaid.render()` call needs.
   - No third-party render dependency (mermaid.ink) or extra Cloudinary
     uploads for diagrams — only `audio_service.py` still uses Cloudinary.
   - Diagrams become themeable/interactive/responsive in the browser
     instead of a fixed-size baked PNG.
   - Frontend now owns Mermaid syntax validation at render time — the
     escaping rules in `blog_compiler.py`'s system instructions (no
     `()[]{}"'` inside labels, always-quoted labels) still matter and
     should stay, since a malformed diagram now fails visibly in the
     user's browser instead of being caught server-side before shipping.
5. ✅ **Podcast compile** (`app/services/podcast_compiler.py`) — one LLM
   call, now on **Groq** (`openai/gpt-oss-120b`); originally built on
   Gemini 2.5 Flash alongside the blog, moved to Groq in the same switch
   (see below). Takes the already-compiled blog as input specifically so
   the prompt can instruct the model *not* to reuse its structure/
   analogies/examples. Two hosts (HOST_A curious/asking, HOST_B explaining
   informally), instructed to include at least one real disagreement/
   correction/tangent. Unlike the blog, subtopics are **not** validated as
   one-section-per-entry (that would force the checklist-y structure the
   feature explicitly wants to avoid) — instead the model returns
   `subtopics_covered`, validated in code as a superset check against
   `recommended_scope`, so coverage is still enforced without constraining
   structure or order. Smoke-tested end-to-end (gap analysis → sources →
   blog → podcast), first on Gemini (46 dialogue lines, all 7 subtopics
   covered, opened with a Docker-solo-vs-orchestra analogy distinct from
   the blog's), then again after the Groq switch (31 lines, all subtopics
   still covered).

   **All-Groq switch**: on explicit direction to not use Gemini anywhere in
   Loop in, both `blog_compiler.py` and `podcast_compiler.py` were moved
   from `google.genai`/Gemini 2.5 Flash to the `groq` SDK/`openai/gpt-oss-120b`
   (same client pattern as `gap_analyzer.py`). First attempt hit a real
   wall immediately: Groq's on-demand tier caps requests at **8,000
   tokens/min**, and the blog prompt with full-length scraped sources (one
   was 28K+ chars alone) came in at ~16,600 tokens — a hard `413` from the
   API, not a transient error, so retrying via `tenacity` wouldn't have
   helped. Fixed by capping prompt size on both ends:
   - `blog_compiler.py`: sources truncated to `MAX_SOURCE_CHARS=600`,
     capped at `MAX_SOURCES_PER_SUBTOPIC=2`; sections capped to ~150-250
     words in the system instructions (bounds output tokens too, not just
     input).
   - `podcast_compiler.py`: sources truncated to `MAX_SOURCE_CHARS=400`,
     capped at `MAX_SOURCES_TOTAL=4`; the blog is now passed as a
     per-section one-line summary (`MAX_SECTION_SUMMARY_CHARS=150`) instead
     of full section content — enough to say "don't repeat this angle"
     without re-feeding the whole article back in; dialogue capped to
     ~20-30 turns in the system instructions.
   Re-ran the full pipeline after these caps: no more `413`s, all outputs
   still validate correctly on the smaller budget.

   **"Sounds like a viva, not a conversation" fix**: user feedback on a real
   generated script — HOST_A asked a question every single turn and HOST_B
   answered it fully, every time, like an interview/quiz rather than two
   people talking. Root cause: the original prompt literally assigned
   HOST_A = "curious, asks questions" and HOST_B = "explains" as fixed
   roles, so the model did exactly that, consistently. Two changes:
   1. Rewrote both host descriptions so neither has a fixed
      question-asker/answerer role, and added an explicit "avoid the
      interview pattern" section — but abstract "don't do X" instructions
      alone barely moved the needle (still ~71% of lines ending in "?" on
      the next test run).
   2. What actually worked: adding a short **few-shot style example**
      (an unrelated topic — a standup-meetings tangent — showing uneven
      turn lengths, statements-not-questions, an unprompted anecdote, a
      short reaction line) plus **hard numeric constraints** ("at most 40%
      of lines end in '?'", "no 2+ consecutive same-host question lines",
      "at least 3 lines under 6 words"). Re-tested: question-ending lines
      dropped to 29%, visibly more statements/reactions instead of
      lockstep Q&A.
   3. Added a **code-level backstop**, not just a prompt hope: `compile_podcast`
      now counts lines ending in `?` and raises (triggering the existing
      `tenacity` retry, a fresh sample at temperature=0.7) if more than 50%
      of lines are questions — the interview pattern is now enforced, not
      just requested.
   **Still imperfect**, noted honestly rather than declared fixed: the
   required "at least one genuine disagreement/tangent" didn't reliably
   show up in the improved run — HOST_B still does most of the explaining,
   it just reads less like a quiz now. That requirement isn't
   code-enforced yet the way the question-ratio one is; worth doing the
   same treatment (count/detect and retry) if it keeps not showing up.
6. ✅ **Podcast audio** (`app/services/audio_service.py` additions —
   `generate_podcast_audio_and_upload` / `create_podcast_audio`) — added
   alongside the existing single-voice functions, nothing removed or
   changed there. Each dialogue line is synthesized with a different
   `edge-tts` voice per host (`HOST_A` → `en-US-AvaNeural`, `HOST_B` →
   `en-US-AndrewNeural` — picked for a clear male/female contrast so hosts
   are easy to tell apart by ear), stitched into one MP3 with `pydub`
   (350ms silence between lines for natural pacing), and uploaded to
   Cloudinary via the same config already in the file, into its own
   `loop_in_podcast` folder (kept separate from the daily pipeline's
   `looplearn_audio` folder, which is untouched). Returns
   `(audio_url, line_timestamps)` — `line_timestamps` is line-level
   (`{host, text, start, end}` in seconds against the final stitched
   track), not word-level, but enough to sync a transcript view to the
   audio. Runs entirely in memory (see the follow-up note below) — no
   audio ever touches local disk. `pydub` added to `requirements.txt`.
   `ffmpeg` confirmed available locally (`ffmpeg version 8.0`, Homebrew).
   Smoke-tested with a real 4-line two-host dialogue: audio uploaded,
   `ffprobe`-verified duration (21.95s) matches the computed timestamps
   almost exactly, confirming the stitching math is correct.

   **Render ffmpeg blocker — resolved.** Confirmed with the user: Render
   service is on the **native Python runtime** (no Dockerfile/render.yaml in
   this repo, matches what I found), which does not ship `ffmpeg`. Fixed
   with `static-ffmpeg` (pip dependency, no Dockerfile/build-command change
   needed) instead of two other approaches that were tried and rejected:
   - `imageio-ffmpeg` was tried first (bundles `ffmpeg` in the wheel itself,
     no runtime download) but doesn't include `ffprobe` — and pydub's
     `AudioSegment.from_file` calls `ffprobe` unconditionally via
     `mediainfo_json`, even with `format="mp3"` passed explicitly. Confirmed
     by literally stripping `ffmpeg`/`ffprobe` off `PATH` locally and
     watching it fail with `FileNotFoundError: ffprobe`.
   - Then tried setting `AudioSegment.ffprobe = <path>` after switching to
     `static-ffmpeg` (which bundles both binaries) — still failed the same
     way. Read pydub's actual source (`pydub/utils.py`,
     `get_prober_name()`): it only ever does `which("ffprobe")` against
     `PATH` — there is no `AudioSegment.ffprobe`-style override in pydub at
     all; setting that attribute silently does nothing.
   - **Actual fix**: prepend the directory containing `static-ffmpeg`'s
     resolved binaries onto `os.environ["PATH"]` at import time in
     `audio_service.py`, so `which("ffprobe")` finds them like it would find
     a system install. Also set `AudioSegment.converter` explicitly (that
     one *is* respected by pydub, unlike `.ffprobe`).
   - Binaries are resolved once, eagerly, at module import (not lazily
     inside the request path) — `static-ffmpeg` downloads them from GitHub
     on first use per process, so this way the download lands at
     cold-start, not silently inside a user's first Loop-in request.
   - **Verified for real**, not just read about: re-ran
     `create_podcast_audio` with `/opt/homebrew/bin` (where local `ffmpeg`/
     `ffprobe` live) stripped from `PATH` entirely — confirmed
     `shutil.which("ffmpeg")` and `which("ffprobe")` both returned `None`,
     and the podcast audio still generated and uploaded correctly. Also
     re-ran with normal `PATH` afterward to confirm no regression.
   - `requirements.txt`: removed `imageio-ffmpeg` (tried, insufficient),
     added `static-ffmpeg`.
   - Residual, honestly-flagged risk: `static-ffmpeg` fetches its binaries
     from `github.com/zackees/ffmpeg_bins` at first use — a third-party
     GitHub release, not a package registry. If GitHub is unreachable from
     Render at cold-start, podcast audio generation fails until it is. Not
     tested against Render's actual network conditions, only reasoned about
     — this is the one part of "does it work on Render" that remains
     genuinely unverified.

   **Follow-up fix, found running the actual pipeline end-to-end (not the
   handwritten smoke test)**: `edge-tts` deterministically throws "No audio
   was received" for a line with no speakable content — empty text, or
   punctuation-only text like `"..."`. This isn't rare: real LLM-generated
   dialogue produced exactly such a line. Confirmed it's deterministic, not
   transient, by isolating it (`_synthesize_line_to_file` failed the same
   way every time on the same bad input) — so a `tenacity` retry (added
   first, reasonably, since the error *sounds* like a network hiccup) was
   the wrong fix and left in only as a safety net for genuine transient
   failures. The real fix: skip any dialogue line whose text has no
   `[A-Za-z0-9]` character at all, same place the existing empty-string
   check already lived. Also cleaned up a stray duplicate `import re` in
   the file while touching it. Re-verified against the isolated failing
   case, then against a full real run (gap analysis → sources → blog →
   podcast → audio) with actual LLM-generated dialogue: 34 lines, all 34
   produced audio and timestamps, no drops, final track ~237s.

   **Stalled-job fix — found during live frontend testing, not a unit
   test.** A real browser-triggered job sat at `status: "running"` for
   20+ minutes with no error — far past the normal 3–5 minute run time,
   and with no error ever recorded (the job wrapper's `except` never
   fired, meaning nothing had failed — something was just blocked).
   Investigated rather than guessed: confirmed `DDGS` already defaults to
   a 5s `timeout` and `trafilatura`'s `DOWNLOAD_TIMEOUT` defaults to 30s
   (checked both libraries' actual source/config), ruling out source
   gathering. That left `edge_tts.Communicate(...).stream()`, which has
   **no timeout at all** — and after ~10+ full runs today alone, hitting
   Microsoft's TTS endpoint hard enough to plausibly trigger rate-limiting
   that hangs the websocket rather than erroring. Fixed in
   `audio_service.py`: split `_synthesize_line_to_file` into a raw
   `_do_synthesize_line` plus a wrapper that runs it under
   `asyncio.wait_for(..., timeout=PER_LINE_SYNTHESIS_TIMEOUT_SECONDS=25)`,
   still inside the existing `tenacity` retry so each retry attempt gets
   its own fresh timeout window rather than sharing one. Verified the fix
   actually works, not just that it looks right: monkeypatched
   `_do_synthesize_line` to hang forever (`asyncio.sleep(999)`) with a
   shrunk timeout/retry config, and confirmed `create_podcast_audio`
   returned cleanly in 5s with `url: None` instead of hanging — then
   re-ran a normal healthy case to confirm no regression. Groq calls
   (gap analysis/blog/podcast) were left alone — no evidence of hanging
   there across many real calls today, only fast responses or clear
   400/413 errors, so no speculative fix added.

   **Went fully in-memory — no local disk writes at all, on user request.**
   The original implementation wrote each line's audio to a named temp
   file, read it back for `pydub`, then exported the stitched result to
   another temp file before uploading — all cleaned up after, but still
   real (if brief) writes to the server's disk. Rewrote to avoid disk
   entirely: `_do_synthesize_line` now returns raw `bytes` instead of
   writing a file; `AudioSegment.from_file` reads from an `io.BytesIO`
   wrapping those bytes (`pydub` pipes bytes to `ffmpeg` regardless of
   whether the source is a path or a file-like object, so this needed no
   `ffmpeg`-side change); the final stitched export goes to another
   `io.BytesIO` via `combined.export(buffer, format="mp3")`; and
   `cloudinary.uploader.upload()` is called directly on that buffer
   (Cloudinary's SDK accepts a file-like object, not just a path) with an
   explicit `format="mp3"` since there's no filename to infer it from
   anymore. `topic_slug` is now only used to build a readable Cloudinary
   `public_id`, not a filename. Verified concretely, not just by removing
   the cleanup code: ran the new version and confirmed zero `.mp3` files
   existed in the working directory both before and after the run (the
   only files present were stale leftovers from *before* this fix — an
   earlier stalled job's orphaned temp files from a forced process kill,
   since a killed process never reaches its `finally` cleanup — and those
   were removed separately, not created by the new code).
7. ✅ **Orchestration** (`app/services/loop_in_service.py`) — `run_loop_in`
   runs steps 1–6 in order, returns `{gap_analysis, blog, podcast_script,
   podcast_audio_url, podcast_timestamps}`. Thin by design — no error
   handling of its own; a failure in any step propagates up to the job
   wrapper, which is where failure is actually recorded (§2 step 8). If
   podcast audio generation fails, the result still returns with
   `podcast_audio_url: None` rather than throwing away the (successfully
   generated) gap analysis/blog/script — a partial result beats none.
8. ✅ **Async job wrapper + ownership fix** (`app/services/loop_in_job_service.py`,
   `app/models/loop_in_jobs.py`, `app/routes/loop_in_routes.py`) — **NOT**
   built on the existing `pipeline_jobs` table as originally planned.
   `pipeline_jobs` backs the daily pipeline, which has no per-user concept
   at all (it's global content, not per-request), so retrofitting `user_id`
   onto it would've been awkward. Instead: a dedicated `loop_in_jobs` table
   (`job_id, user_id, topic, intent, status, result, error, timestamps`,
   `user_id` a real FK to `users(id)`) — the ownership gap from §6.1 doesn't
   exist here even transiently, since the table was designed with an owner
   from the start rather than retrofitted. Registered in
   `app/models/schema.py`'s `init_db()` alongside the other tables.
   - `POST /api/loop-in/run` (`@require_auth`) validates topic/intent
     (reusing `gap_analyzer.py`'s `MAX_TOPIC_LENGTH`/`MAX_INTENT_LENGTH`
     rather than duplicating the limits), starts the background job scoped
     to the caller's `user_id`, returns `202 {job_id, status}`.
   - `GET /api/loop-in/status/<job_id>` (`@require_auth`) checks
     `job.user_id == caller.user_id` (or caller is admin) before returning
     anything — a non-owner gets the same `404 Job not found` as a
     nonexistent job, not a `403`, so job existence isn't leaked either.
   - Both routes registered in `run.py` alongside the existing blueprints.

   **Verified for real, not just unit-level**: ran the actual Flask route
   through `app.test_client()` against the real dev database (a real user
   created via `get_or_create_user`, a real signed JWT) —
   - unauthenticated `POST /run` → `401`
   - empty topic → `400 {"error": "topic is required"}`
   - a second, different user polling the first user's `job_id` → `404`
     (ownership enforced)
   - the legitimate owner polling to completion: job went
     `pending` → `running` (~168s, full real pipeline) → `completed`, with
     a real result — 6-subtopic gap analysis, a 6-section blog, a 40-line
     podcast script, and a working Cloudinary podcast audio URL.
   This is the first point in the build where Loop in was exercised as an
   actual authenticated HTTP API, not just as directly-called Python
   functions.

---

## 3. Monetization — pay-per-use credits 🚧 (designed, not built)

Confirmed against the actual repo: `app/services/razorpay_service.py` exists
today but only supports the recurring Subscription API — `create_order` (one
-time orders) and `loop_in_credits.py`/`credit_routes.py` don't exist yet.

We compared four models (perk+overage tied to domain subs, pure pay-per-use
credits, a standalone "Loop in" subscription tier, and free-with-caps to
gather usage data first) and **chose pure pay-per-use credits**, kept fully
separate from the existing per-domain subscription system — because Deep
Dive's cost is per-request (fresh LLM calls + scraping + TTS every time),
unlike the daily articles which are generated once and shared across every
subscriber of a domain.

- **Credit ledger** (`loop_in_credits.py`) — one row per user, atomic
  `try_consume_credit()` (deduct 1 only if balance > 0, race-safe) and
  `refund_credit()` if a job fails after the credit was already spent.
- **One-time Razorpay Orders** (`razorpay_service.py` addition: `create_order`)
  — a separate code path from the existing Subscription API, since credit
  packs are one-off purchases, not recurring billing.
- **Credit pack purchase + webhook** (`credit_routes.py`) — `GET /packs`,
  `GET /me` (balance), `POST /purchase` (creates a Razorpay order),
  `POST /webhook` (HMAC-verified `payment.captured` handling), `POST /confirm`
  (fallback re-fetch from Razorpay, mirroring the existing subscription
  `/confirm` pattern).
- **Example pack pricing** used in the code (₹15/1 credit, ₹59/5 credits,
  ₹199/20 credits) — these are placeholder numbers I picked for the code to
  run, **not a pricing decision we've actually made**. Real pricing should
  be set once you know your actual per-request LLM/TTS cost (see §4).
- **Access model**: not gated by content visibility like `today-topics` —
  gated by *action*. The `/loop-in/run` route checks/spends a credit
  before spawning the job; a `402` with `{error: "insufficient_credits",
  balance}` tells the frontend to open the credit-pack modal.

---

## 4. LLM provider / cost discussion

- **Currently assumed**: Gemini 2.5 Flash (same as the existing daily
  pipeline), 3 calls per Loop in (gap analysis + blog + podcast).
- **Grok (xAI)** — investigated and ruled out for cost savings. Its free tier
  is consumer-chat-only (X/grok.com); the API bills per token from the first
  request regardless of spend tier. Not cheaper than Gemini.
- **Groq (the separate LPU inference company — easy to confuse with Grok)**
  — has a genuine free API tier for open models. For **GPT-OSS 120B**: 1,000
  requests/day, 8,000 tokens/min, 200,000 tokens/day. Rough math for our
  workload (~8–12K tokens per Loop in across 2–3 calls) → **~15–25 free
  Loop ins/day**, similar order of magnitude to Gemini's free tier, not a
  10x win.
- **Where Groq actually wins**: paid-tier price. GPT-OSS 120B costs
  $0.15/M input, $0.60/M output — roughly **$0.003 per Loop in** at real
  volume. Negligible next to any credit price we'd charge.
- **Blog and podcast compilers can run on the same provider/model** —
  confirmed they're independent calls with no coupling; Groq's API is
  OpenAI-SDK-compatible and supports JSON schema structured output, so the
  swap is mechanical (change the client, not the calling code).
- **Suggested hybrid — ✅ implemented**: keep Gemini for quality-sensitive
  blog/podcast writing, route the small, mechanical gap-analysis call to
  Groq's free/cheap tier (`app/services/gap_analyzer.py` now runs on
  `openai/gpt-oss-120b` via Groq) — cuts Gemini usage by a third at no
  quality cost, since gap analysis is closer to classification than
  writing.
- **Caveat**: all the free-tier/pricing numbers above came from third-party
  pricing blogs, not the providers' live docs, and shift often. Re-check
  console.groq.com/docs/rate-limits and ai.google.dev before sizing anything
  around these figures.

---

## 5. Still open — discussed but not built

- **User-uploaded materials**: let the user attach their own notes/PDF/docx
  and have that feed into the pipeline. The real design question isn't the
  extraction mechanics (that's mechanical — PyMuPDF/python-docx/plain text)
  — it's **where the upload sits relative to gap analysis**: does it shrink
  the gaps (treated as "the user already knows this"), or just add context
  while gaps are computed the same way regardless? Not yet decided.
- **Subtopic structure**: partially solved as a side effect of the diagram
  work — the blog schema now requires exactly one section per
  `recommended_scope` entry, so the article is already organized by
  subtopic. Whether we want a *deeper* tree (subtopics with their own
  sub-subtopics) is still open.

---

## 6. Recommendations — things worth adding that haven't come up yet

### 6.1 Fix job ownership — ✅ done
Built as a dedicated `loop_in_jobs` table (§2 step 8) with a real `user_id`
FK from the start, rather than retrofitting `pipeline_jobs`. Ownership
enforced in `GET /api/loop-in/status/<job_id>`, verified with a real
second-user 404 test against the live route.

### 6.2 A "My Loop ins" library
Right now a completed Loop in lives only in one job's `result` JSONB with
no listing endpoint. Since the user paid a credit for it, they'll expect to
revisit it later — add `GET /loop-in/history` (or similar) so it's not
effectively single-use/disposable.

### 6.3 Content moderation on the topic itself
Topic + intent are free text that goes straight into LLM prompts and drives
web scraping and public-facing audio generation. Worth a lightweight
safety/topic check *before* spending a credit and running the expensive
pipeline — otherwise you're both generating and paying for content on
whatever anyone types.

### 6.4 Caching/deduplication for popular topics
If two different users request something close to the same topic+intent
(e.g. "explain Kubernetes for a backend dev"), you're re-running the full
pipeline and re-paying the LLM/TTS cost each time. A hash-based cache keyed
on normalized topic+intent (with a short TTL, or permanent with a "refresh"
option) could cut real cost meaningfully once you have any traffic.

### 6.5 Quality floor / softer failure path
If source scraping comes back empty for a topic (obscure/newer topic, DDG
rate-limited, etc.), the pipeline still runs on gap analysis + intent alone
and produces *something*, but it may be thin. Right now that's not
distinguished from a "good" run, and the credit isn't refunded because
nothing threw an exception. Consider a minimum-source-count check that
either retries the scrape or flags the result as lower-confidence.

### 6.6 Input/upload size limits — ✅ partially done
Topic/intent length caps landed as part of `gap_analyzer.py` (§2 step 1) —
cheap enough to add at the same time rather than as a follow-up. Upload file
size cap still open, blocked on the upload feature itself (§5).

### 6.7 Loop this back into your existing daily pipeline
Real product synergy worth considering: track which Loop in topics get
requested most, and feed the popular ones (or their `recommended_scope`
subtopics) into the existing `concept_nodes`/`concept_edges` graph as
candidates for the free daily pipeline — similar to how `topic_compiler`
already suggests `child_topics`. Turns paid, one-off demand into free,
evergreen content, and tells you what your audience actually wants without
guessing.

### 6.8 Set-expectations UI for the wait — ✅ done
A Loop in takes 30–90+ seconds (3 LLM calls + scraping + TTS). Built into
the frontend's `LoopInGeneratingPanel` (§7) — a rotating phase label
("Analyzing what you already know" → "Researching your subtopics" →
"Writing the deep-dive article" → "Recording the two-host podcast") plus
explicit copy ("Deep dives take 60–90+ seconds...") so a paying user isn't
left staring at a bare spinner.

---

## 7. Frontend — built and verified in the browser

Built against the actual frontend repo (`~/Developer/react/looplearn` —
React 19 + TypeScript + Vite + Tailwind v4 + Redux Toolkit + react-router-dom
v7), matching its existing design language rather than introducing a new
one: `rounded-3xl` cards, `font-black tracking-tight` headings, uppercase
`tracking-widest` pill badges, `Loader2`/lucide icons, the existing
`AudioPlayer` component, and the same `mermaid` (`theme: neutral`,
`look: handDrawn`) pattern already used in `Todays.tsx` for diagrams.
Emerald was picked as Loop In's accent color specifically because blue
(daily briefing) and purple (workspaces) were already taken by other
features on the Dashboard — keeps the three at a glance distinguishable.

- **`src/api/loopIn.ts`** — typed client (`run`, `getStatus`) matching the
  existing `subscriptionApi` pattern, with TS interfaces mirroring the
  backend's actual JSON shape (`GapAnalysis`, `Blog`, `PodcastScript`,
  `LoopInResult`, `LoopInJob`).
- **`src/pages/LoopIn.tsx`** — the whole flow as one page (form → poll →
  results → error), matching how `Todays.tsx` also keeps a lot inline
  rather than over-splitting into components. Polls `GET /status/<job_id>`
  every 5s via `setInterval`, cleaned up on unmount and on completion.
- **`src/components/skeletons/LoopInGeneratingPanel.tsx`** — the §6.8 wait
  UI. Explicitly commented in the code that the phase cycling is
  time-based, not real backend progress — honest about what it is.
- **`src/components/loopIn/GapAnalysisPanel.tsx`** — "You asked for" vs
  "You'll also need" as blue/emerald pill grids.
- **`src/components/loopIn/BlogPanel.tsx`** — renders `blog.sections`,
  each optionally with a mermaid diagram (own `DiagramBlock` sub-component,
  one `mermaid.run()` per diagram since sections can have independent
  diagrams, unlike `Todays.tsx`'s single-diagram-per-article case).
- **`src/components/loopIn/PodcastPanel.tsx`** — reuses the existing
  `AudioPlayer` as-is, plus a collapsible transcript with per-host chat
  bubbles (blue for HOST_A/Maya, violet for HOST_B/Leo, left/right aligned).
- Router (`src/routes/router.tsx`), `Navbar.tsx` (desktop + mobile links),
  and `Dashboard.tsx` (new emerald "Loop In" entry card, styled to match
  the existing "Today's Briefing" card) all updated.

**Verified for real in a live browser, not just code review or `tsc`:**
- `npx tsc -b` / `npx eslint` on the new/changed files: zero new errors
  (pre-existing errors in untouched files like `Pricing.tsx` confirmed via
  `git stash` to predate this work).
- Ran the actual local Flask backend (port 5001, via a temporary Vite dev
  proxy in `vite.config.ts` — added only because the design's existing CORS
  allowlist is `localhost:5173`, which the user's own already-running dev
  server was occupying) and drove the real form → submit → poll → render
  flow with `mcp__claude-in-chrome`, using a real JWT for a real DB user.
- Confirmed visually: form validation/char-counter, the generating panel's
  phase cycling advancing correctly over real elapsed time, the completed
  view's gap-analysis pills, the podcast player actually playing real
  audio, the collapsible transcript with correctly-aligned/colored host
  bubbles (and genuine banter in the actual content — "you're definitely
  the pod-caster" / "it kept scaling to zero—turns out I forgot to set a
  minReplicas"), and a multi-node mermaid diagram rendering correctly
  inside a blog section.
- Hit a real stall during this exact testing session — see the "Stalled-job
  fix" note under §2 step 6 — found specifically *because* this was tested
  as a live user flow, not just unit-level.
- One local-only artifact from this testing, not shipped: `.env.local`
  (`VITE_API_BASE_URL=`, gitignored via the existing `*.local` rule) and
  the temporary `server.proxy` block in `vite.config.ts` — both should be
  reverted/left out of any commit from this session, since they only exist
  to route around the user's own dev server occupying port 5173.
