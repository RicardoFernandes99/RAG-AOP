from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

from vector import retriever


def format_documents(documents) -> str:
    formatted_chunks = []

    for document in documents:
        source = document.metadata.get("source", "unknown")
        source_name = source.split("\\")[-1].split("/")[-1]
        page = document.metadata.get("page")
        formatted_chunks.append(
            f"Document: {source_name}\n"
            f"Page: {page}\n"
            f"Content: {document.page_content}"
        )

    return "\n\n".join(formatted_chunks)


model = OllamaLLM(model="llama3.2",
                   temperature=0.2,
                   top_p=0.9,
                   max_tokens=2048,
                   top_k=40,
                   seed=42,
                   )

template = """
You are an expert accountant specialized in Portuguese accounting rules.

Use ONLY the information from the provided documents to answer the question.

If the answer cannot be found in the documents, say:
"I cannot find the answer in the provided documents."

Documents:
{documents}

Question:
{question}

Respond in the following format:

Answer:
<detailed explanation in Portuguese from Portugal, using the retrieved documents as reference,
 and citing them when relevant>

Sources:
<only the document file names used, one per line>
"""

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model


while True:
    question = input("Ask your question (q to quit):")
    if question == "q":
        break

    documents = retriever.invoke(question)
    formatted_documents = format_documents(documents)
    result = chain.invoke({"documents": formatted_documents, "question": question})
    print(result)
