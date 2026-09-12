from app.services.gap_analyzer import analyze_gaps
from app.services.loop_in_source_service import gather_sources
from app.services.blog_compiler import compile_blog
from app.services.podcast_compiler import compile_podcast
from app.services.audio_service import create_podcast_audio


def run_loop_in(topic: str, intent: str, audio_slug: str) -> dict:
    """
    Runs the full Loop in pipeline end to end: gap analysis -> source
    gathering -> blog compile -> podcast script compile -> podcast audio.
    Returns {gap_analysis, blog, podcast_script, podcast_audio_url}.
    """
    gap_analysis = analyze_gaps(topic, intent)
    sources = gather_sources(gap_analysis["recommended_scope"])
    blog = compile_blog(topic, intent, gap_analysis, sources)
    podcast_script = compile_podcast(topic, intent, gap_analysis, sources, blog)
    podcast_audio_url, podcast_timestamps = create_podcast_audio(podcast_script["dialogue"], audio_slug)

    return {
        "gap_analysis": gap_analysis,
        "blog": blog,
        "podcast_script": podcast_script,
        "podcast_audio_url": podcast_audio_url,
        "podcast_timestamps": podcast_timestamps,
    }
