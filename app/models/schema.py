from app.models.graph import create_graph_tables, seed_domains
from app.models.sources import create_sources_table
from app.models.daily_posts import create_daily_post_table
from app.models.daily_posts import create_daily_post_sources_table
from app.models.topic_history import create_topic_history_table
from app.models.topic_sources import create_topic_sources_table
from app.models.compiled_topics import create_compiled_topics_tables
from app.models.pipeline_jobs import create_pipeline_jobs
from app.models.article_candidate import create_article_candidate
from app.models.published_articles import create_published_article, create_article_visibility_table
from app.models.user import create_user_table,create_plans_table

def init_db():

    create_graph_tables()
    create_sources_table()
    create_daily_post_table()
    create_daily_post_sources_table()
    create_topic_history_table()
    create_topic_sources_table()
    create_compiled_topics_tables()
    create_pipeline_jobs()
    create_article_candidate()
    create_published_article()
    create_article_visibility_table()
    create_user_table()
    create_plans_table()
    


    seed_domains()

    print("✅ DB initialized fully")
