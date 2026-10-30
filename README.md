🍳 Indian Kitchen Asma — AI Cooking Assistant

Your Personal Recipe Assistant, Powered by Retrieval-Augmented Generation (RAG)

An AI-powered cooking assistant that understands recipe-related questions and provides answers using real cooking transcripts from the Indian Kitchen Asma YouTube channel.

Instead of relying entirely on an LLM's general knowledge, this project uses Retrieval-Augmented Generation (RAG) to retrieve relevant recipe information from a custom dataset and generate context-based answers using a locally running Large Language Model.

🌟 Project Overview

Indian Kitchen Asma AI is designed to make cooking information easier to access.

The system processes cooking videos, converts speech into English transcripts, transforms the transcripts into embeddings, and retrieves relevant information when a user asks a question.

For example:

How do I prepare Gond Laddu?

What ingredients are required for Bhelpuri?

Explain the preparation steps for Paneer Biryani.

How can I make crispy chicken lollipop?

The assistant searches the available recipe data and generates an answer based on the retrieved information.

✨ Key Features

Recipe-Based Question Answering: Ask questions about recipes available in the dataset.

Hindi-to-English Transcription: Convert Hindi cooking audio into English transcripts using Whisper.

Semantic Search: Retrieve relevant recipes based on the meaning of a question rather than exact keyword matching.

Local LLM Integration: Generate responses using Ollama without requiring a paid cloud LLM API.

Context-Based Responses: Generate answers using retrieved recipe information.

Recipe Dataset: Store processed recipe transcripts in structured JSON files.

Source Information: Include recipe titles and available timestamps to help identify the original video content.

🛠️ Technology Stack

The project uses Python, NLP, machine learning libraries, local LLMs, and data-processing tools.

Technology

Purpose

Python

Main programming language used to build the complete workflow.

Ollama

Runs Large Language Models locally for generating answers.

BGE-M3

Converts recipe transcripts and user questions into numerical vector embeddings.

Scikit-learn

Calculates cosine similarity to identify relevant recipe information.

NumPy

Handles numerical operations and embedding vectors.

Pandas

Organizes and processes structured embedding data.

Joblib

Saves and loads generated embedding data.

Whisper

Converts Hindi cooking audio into English text transcripts.

BeautifulSoup4

Extracts YouTube video information from HTML content.

Requests

Sends HTTP requests to retrieve web page data.

JSON

Stores structured recipe transcripts and processed data.

Why These Technologies?

Ollama + BGE-M3

Ollama provides local LLM inference, while BGE-M3 generates embeddings that represent the semantic meaning of recipe text.

Scikit-learn + NumPy

Cosine similarity compares the question embedding with stored recipe embeddings to find the most relevant results.

Whisper

Whisper helps convert Hindi cooking instructions into English transcripts, making the recipe information easier to process.

BeautifulSoup4 + Requests

These libraries are used to retrieve and extract YouTube video metadata such as titles and other available information.

Pandas + Joblib + JSON

These tools help organize, store, and reuse the processed recipe data and embeddings.

🎯 Project Goals

Build a practical RAG-based AI application.

Understand how embeddings and semantic search work.

Explore local LLM inference using Ollama.

Integrate speech-to-text processing into an AI workflow.

Develop a useful cooking assistant using real-world recipe data.

🚀 Future Improvements

Develop an interactive web-based chat interface.

Add more cooking videos and recipe transcripts.

Improve recipe retrieval accuracy.

Implement more advanced document chunking strategies.

Display direct YouTube video links with timestamps.

Improve response quality and reduce hallucinations.

Add multilingual question answering.

👨‍💻 Developer

Qasim Khan

BCA Student | Python Developer | Aspiring Data Analyst

Interested in Python, Machine Learning, Data Science, Web Development, and Generative AI.

⭐ If you find this project interesting, consider giving the repository a star!

Built with curiosity, Python, and a passion for AI.
