from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
import os

def get_llm():
    return ChatMistralAI(
        model=os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
        api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.3
    )

def split_transcript(transcript: str) -> list:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=300,
        length_function=len,
    )
    return text_splitter.split_text(transcript)

DOCUMENT_SUMMARY_SYSTEM = (
    "You are a professional document analyst. Create a comprehensive summary of the following document.\n"
    "- State what kind of document it is and its main purpose\n"
    "- List the key points, decisions, obligations or conclusions\n"
    "- Extract important entities: people, organizations, dates, amounts and deadlines\n"
    "- Note any risks, deadlines or action items\n"
    "- Keep it professional, clear, and concise (1-2 paragraphs, then bullet points)."
)


def summarize(transcript: str, kind: str = "meeting") -> str:
    """kind: 'meeting' (audio/video transcript) or 'document' (PDF / DOC / DOCX text)."""
    llm = get_llm()
    chunks = split_transcript(transcript)

    meeting_system = (
        "You are a professional meeting summarizer. Create a comprehensive summary of the following meeting transcript.\n"
        "- Identify key decisions made\n"
        "- List major action items and assignees\n"
        "- Note any risks or dependencies\n"
        "- Keep it professional, clear, and concise (1-2 paragraphs)."
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", DOCUMENT_SUMMARY_SYSTEM if kind == "document" else meeting_system),
        ("user", "{transcript}"),
    ])

    summarize_chain = {"transcript": RunnablePassthrough()} | prompt | llm | StrOutputParser()

    if len(chunks) <= 1:
        return summarize_chain.invoke(transcript)

    chunk_summaries = [summarize_chain.invoke(chunk) for chunk in chunks]
    combined_transcript = "\n\n".join(chunk_summaries)

    combined_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a professional " + ("document analyst" if kind == "document" else "meeting summarizer")
            + ". Combine the following chunk summaries into one final professional "
            + ("document" if kind == "document" else "meeting") + " summary with bullet points."
        ),
        ("user", "{transcript}"),
    ])
    combine_chain = {"transcript": RunnablePassthrough()} | combined_prompt | llm | StrOutputParser()
    return combine_chain.invoke(combined_transcript)

generate_title_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a professional meeting summarizer. Create a creative and interesting title for the following meeting transcript. "
        "Keep it short, interesting, and relevant to the meeting."
    ),
    ("user", "{transcript}"),
])

generate_document_title_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a professional document analyst. Create a short, clear and descriptive title for the following document. "
        "Return only the title."
    ),
    ("user", "{transcript}"),
])

def get_title(transcript: str, kind: str = "meeting") -> str:
    llm = get_llm()
    prompt = generate_document_title_prompt if kind == "document" else generate_title_prompt
    title_chain = {"transcript": RunnablePassthrough()} | prompt | llm | StrOutputParser()
    # a document title only needs the opening of the text (keeps long documents cheap)
    return title_chain.invoke(transcript[:6000] if kind == "document" else transcript)



    


