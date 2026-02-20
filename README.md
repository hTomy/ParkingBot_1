# 🚗 Parking Assistant Chatbot — RAG + SQL Agent

A **LangGraph + LangChain** powered chatbot that combines Retrieval-Augmented Generation (RAG) with SQL querying to provide intelligent parking assistance.

✨ **Key Features**

* 🧠 **RAG retrieval** powered by **Weaviate + LlamaIndex**
* 🗄️ **SQL querying** via `SQLDatabaseToolkit`
* 🧩 Tool-calling agents for bookings and knowledge queries
* 📊 Retrieval evaluation with **Precision@K / Recall@K**
* 🔒 Sensitive-data filtering


---

# ⚙️ Initial Setup

## ✅ Prerequisites

Before starting, ensure you have:

* Docker installed
* Python **3.7+**
* Git

---

## 📥 Clone the Repository

```bash
git clone <your-repo-url>
cd <repo-name>
```

---

## 🔐 Environment Configuration

Add environmental variable:

```bash
OPENAI_API_KEY=<your_openai_key>
```

---

## 🐍 Python Environment Setup

In project root create a virtual environment:

```bash
python -m venv .venv
```

### Activate the environment

**Windows**

```cmd
.venv\Scripts\activate
```

**MacOS / Linux**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🗄️ Database & Infrastructure Setup (Docker)

Navigate to the `db_setup` directory and start required services:

```bash
docker-compose up -d
```

This will launch:

* Weaviate vector database
* PostgreSQL database
* Supporting services

After it has started run the init scripts:

```bash
python setup_postgres.py
```

```bash
python setup_weaviate.py
```

---

# ▶️ Running the Chatbot

Start the main application:

```bash
python main.py
```

The chatbot will initialize:

* LangGraph agent
* Retrieval system
* SQL tools
* Vector database connection

---

# 📊 Retrieval Evaluation (Precision@K / Recall@K)

To evaluate retrieval performance, run:

```bash
python test/performance.py
```

This script measures:

* **Precision@K** – How many retrieved chunks are relevant
* **Recall@K** – How many relevant chunks were successfully retrieved

These metrics help tune chunking, embeddings, and retrieval parameters.

---

# Example usage

<img src="img/example_usage.png">

