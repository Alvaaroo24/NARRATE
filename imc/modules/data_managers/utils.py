from langchain_core.prompts import PromptTemplate

from imc.modules.llms.llm import llm



async def create_chat_title_from_query(query):
    template = f"""
    You are an AI chat system. You have to create a short and descriptive title for a chat in base to the first message of the user in that chat. The title will always be in english, regardless of the message language.

    User's message:
    {query}

    Respond ONLY with the title.
    """

    prompt = PromptTemplate(template=template)

    try:
        result = await (prompt | llm).ainvoke({})
        title = result.content
    except Exception as e:
        print(f"Title creation failed via LLM: {e}")
        title = "New chat"
    return title