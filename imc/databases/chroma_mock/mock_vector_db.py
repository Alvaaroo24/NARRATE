from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import AzureOpenAIEmbeddings
import os
from imc.config import settings

def create_chroma_db_from_txt(file_path, persist_directory="imc/databases/chroma_mock"):
    
    index_exists = os.path.exists(os.path.join(persist_directory, "chroma.sqlite3"))
    if index_exists: 
        print(f"Chroma DB already created in: {persist_directory}")
        
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        docs = text_splitter.create_documents([text])

        embeddings = AzureOpenAIEmbeddings(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_base_url,
            azure_deployment=settings.azure_openai_embbeding_model_deployment_name,
            openai_api_version=settings.azure_openai_api_version
        )


        vectordb = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=persist_directory
        )

        vectordb.persist()
        print(f"Chroma DB created and saved in: {persist_directory}")
