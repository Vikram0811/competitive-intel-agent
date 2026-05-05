from langchain_community.tools.tavily_search import TavilySearchResults
import config

def create_search_tool():
    """
    Returns a Tavily search tool configured for the agent.
    max_results controls how many results are returned per search.
    """
    return TavilySearchResults(
        max_results=config.MAX_SEARCH_RESULTS,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
        include_images=False,
    )