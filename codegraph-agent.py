#!/usr/bin/env python3
import os
import sys
import re
from openai import OpenAI
from neo4j import GraphDatabase
from dotenv import load_dotenv
from neo4j.exceptions import Neo4jError

# 🧪 Load .env
load_dotenv()

# 🔐 Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DB = os.getenv("NEO4J_DB")

if not OPENAI_API_KEY:
    print("❌ Missing OPENAI_API_KEY.")
    sys.exit(1)

print(f"Connecting to OpenAI-compatible API at {OPENAI_API_BASE}")
print("Using model: claude-sonnet-4")

# ✅ OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

# 💬 Get prompt
user_prompt = " ".join(sys.argv[1:]).strip()
if not user_prompt:
    print("Usage: codegraph-agent.py <natural language question>")
    sys.exit(1)

# 🧠 Ask LLM
print("\n💬 Prompting LLM to generate Cypher...")
response = client.chat.completions.create(
    model="claude-sonnet-4",
    messages=[
        {
            "role": "system",
            "content": (
                "You are an expert in Cypher and source code knowledge graphs. "
                "Generate Cypher queries to answer questions using the following node types:\n"
                "- JavaClass, JavaMethod, JavaInterface, JavaField\n"
                "- PythonClass, PythonMethod, PythonFunction\n"
                "- File, Directory, Function, Method\n\n"
                "Common relationships include:\n"
                "- HAS_METHOD, HAS_FIELD, IMPLEMENTS, CALLS, IMPORTS\n\n"
                "Only return fields that are present in the graph, such as `.name` and `.qualifiedName`. "
                "Do NOT include `file_path`, `path`, or other non-existent keys. "
                "Do not include markdown or ``` blocks in your response."
            )
        },
        {"role": "user", "content": user_prompt}
    ],
    max_tokens=4096,
    temperature=0.2
)

# 🧹 Extract Cypher from response
cypher_query_raw = response.choices[0].message.content.strip()
cypher_query = re.sub(r"```(?:cypher)?\s*([\s\S]*?)\s*```", r"\1", cypher_query_raw).strip()

print(f"\n🧠 Generated Cypher:\n{cypher_query}\n")

# 🔍 Query Neo4j
print("🔍 Querying Neo4j...\n")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
try:
    with driver.session(database=NEO4J_DB) as session:
        result = session.run(cypher_query)
        records = result.data()
except Neo4jError as e:
    print(f"❌ Neo4j query failed: {e}")
    sys.exit(1)
finally:
    driver.close()

# 📊 Display results
if not records:
    print("No results.")
else:
    for i, record in enumerate(records, 1):
        pretty = ", ".join(f"{k}: {v}" for k, v in record.items())
        print(f"{i}. {pretty}")
