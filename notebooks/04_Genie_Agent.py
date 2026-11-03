# Databricks notebook source
# MAGIC %md
# MAGIC # Module 4 · Create the Genie Agent (35 min)
# MAGIC
# MAGIC **Goal:** business users ask questions in plain language and get **the same numbers as the dashboard**, because
# MAGIC Genie reads the same diamond table and certified metric view.
# MAGIC
# MAGIC | Step | Time | What you do |
# MAGIC |---|---|---|
# MAGIC | 1 | 5 min | Create the Genie Agent on the diamond table and metric view |
# MAGIC | 2 | 7 min | Add instructions |
# MAGIC | 3 | 5 min | Add example SQL and sample questions |
# MAGIC | 4 | 13 min | Ask business-style questions and compare with the dashboard |
# MAGIC | 5 | 5 min | Monitor: review what was asked, and improve |
# MAGIC
# MAGIC **Prerequisite:** Modules 1–3 are done. Genie needs a pro or serverless SQL warehouse and **partner-powered AI**
# MAGIC turned on.

# COMMAND ----------

# MAGIC %pip install -q --upgrade "databricks-sdk>=0.60"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 · Create the Genie Agent (UI)
# MAGIC 1. Open **Genie → New**.
# MAGIC 2. **Add data:** your `policy_diamond` and `policy_metrics` (full names printed below).
# MAGIC 3. **Settings:** title and description from below; choose the serverless SQL warehouse.

# COMMAND ----------

gold = f"{target_catalog}.{target_schema}"
description = "Ask about policy counts, in-force rate and premium by product line, status and issue period."
print(f"Tables:      {gold}.policy_diamond\n             {gold}.policy_metrics\nTitle:       {genie_title}\n"
      f"Description: {description}\nWarehouse:   {warehouse_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 · Add instructions
# MAGIC Open **Instructions → Text** and paste the block printed below. It tells Genie to prefer the certified metric view,
# MAGIC what *in force* and *premium* mean, and how to format answers.

# COMMAND ----------

text_instructions = """You answer questions about annuity and life insurance policies.
- Prefer the certified metric view policy_metrics for KPIs; use MEASURE(<measure>) and GROUP BY the dimensions asked for.
- "In force" or "active" means policy_status = 'In force'. "In-force rate" or "persistency" is in_force_rate.
- Premium means premium_amount: single premium for annuities, annualised planned premium for life. Say so when you add
  annuity and life premium together.
- Product line is Annuity or Life.
- Show rates as percentages with one decimal and amounts in USD with no decimals."""
print(text_instructions)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 · Add example SQL and sample questions
# MAGIC - **Instructions → SQL queries → Add:** paste each question and its SQL from below. Genie learns the pattern
# MAGIC   (`MEASURE()` on the metric view) from these.
# MAGIC - **Settings → Sample questions:** add the four questions printed below.

# COMMAND ----------

example_sql = {
    "How many policies are in force by product line?":
        f"SELECT product_line, MEASURE(in_force_policies) AS in_force_policies, MEASURE(total_policies) AS total_policies\n"
        f"FROM {gold}.policy_metrics GROUP BY ALL ORDER BY in_force_policies DESC",
    "What is the in-force rate by product line and issue year?":
        f"SELECT product_line, issue_year, ROUND(100 * MEASURE(in_force_rate), 1) AS in_force_pct\n"
        f"FROM {gold}.policy_metrics GROUP BY ALL ORDER BY product_line, issue_year",
}
sample_questions = ["How many policies are in force by product line?",
                    "What is the in-force rate by product line and issue year?",
                    "What is the total premium for annuities issued in the last 12 months?",
                    "Which status has the highest average premium for life policies?"]
for q, sql in example_sql.items():
    print(f"-- {q}\n{sql}\n")
print("Sample questions:\n- " + "\n- ".join(sample_questions))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Catch-up cell
# MAGIC Creates (or updates) the same Genie Agent with everything from Steps 1–3.

# COMMAND ----------

nid = iter(f"{i:032x}" for i in range(1, 100))   # Genie needs 32-hex ids, sorted within each list
space = {
    "version": 2,
    "config": {"sample_questions": [{"id": next(nid), "question": [q]} for q in sample_questions]},
    "data_sources": {"tables": [
        {"identifier": f"{gold}.policy_diamond",
         "description": ["Diamond table: one row per annuity or life policy, with product line, standardised status, "
                         "issue date and premium. Built by the ruby → diamond pipeline."]},
        {"identifier": f"{gold}.policy_metrics",
         "description": ["Certified metric view: total_policies, in_force_policies, in_force_rate, total_premium, "
                         "avg_premium. Query measures with MEASURE()."]}]},
    "instructions": {
        "text_instructions": [{"id": next(nid), "content": [text_instructions]}],
        "example_question_sqls": [{"id": next(nid), "question": [q], "sql": [sql]} for q, sql in example_sql.items()]},
}
body = {"title": genie_title, "description": description, "warehouse_id": warehouse_id,
        "serialized_space": json.dumps(space)}
space_id = find_genie_space_id()
if space_id:
    w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=body)
else:
    space_id = w.api_client.do("POST", "/api/2.0/genie/spaces", body=body)["space_id"]
print(f"✅ Genie Agent: {w.config.host}/genie/rooms/{space_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 · Ask business-style questions
# MAGIC In the Genie Agent, ask these and compare each answer with the dashboard:
# MAGIC 1. *How many policies are in force by product line?* It should match the dashboard's *In-force policies* counter.
# MAGIC 2. *What is the in-force rate by product line and issue year?*
# MAGIC 3. *What is the total premium for annuities issued in the last 12 months?*, then follow up with *…and for life?*
# MAGIC 4. Click **Show code** on an answer: Genie used `MEASURE()` on the certified metric view.
# MAGIC
# MAGIC The next cell asks question 1 through the API and prints Genie's SQL and answer:

# COMMAND ----------

msg = w.genie.start_conversation_and_wait(space_id, "How many policies are in force by product line?")
for att in msg.attachments or []:
    if att.query:
        print("Genie SQL:\n", att.query.query)
    if att.text:
        print("\nGenie says:", att.text.content)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 · Monitor and improve
# MAGIC 1. Open **Monitoring** in the Genie Agent: every question, the SQL Genie wrote, and any 👍 / 👎 feedback.
# MAGIC 2. Find an answer you like and click **Add as instruction** (or copy it into a new example SQL query).
# MAGIC 3. Ask a question Genie gets wrong, fix it with a one-line text instruction, and ask again.
# MAGIC
# MAGIC Business users can also reach this agent from **Genie One**.
# MAGIC
# MAGIC ✅ **Module 4 done.** Next: `05_Governance`.
