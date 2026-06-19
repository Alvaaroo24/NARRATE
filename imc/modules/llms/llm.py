import os
from langchain_openai import AzureChatOpenAI
from imc.config import settings


def get_llm(temperature: int = 0, retries: int = 2, verbose: bool = True):

    return AzureChatOpenAI(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_base_url,
        api_version=settings.azure_openai_api_version,
        model_name=settings.azure_openai_model_deployment_name,
        verbose=verbose,
        temperature=temperature,
        max_retries=retries,
    )


llm = get_llm()
