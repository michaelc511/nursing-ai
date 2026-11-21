# Deep dive 16 of 27: Structured Storage (SQL/Postgres)

Nov 19, 2026 · Michael Chang · Status in NurseOps Now: ✅ built (SQLite)

**Part of:** [Remembering the right things: state management in NurseOps Now](../nurseops-now-state.html), section [Implementing Long-Term Memory: External Persistence Architecture (7.3)](../nurseops-now-state.html#implementing-long-term-memory-external-persistence-architecture-7-3) · [All 27 solutions](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives) · [← The Hot/Cold State Architecture](state-15-hot-cold-state-architecture.html) · [Semantic Storage (Vector DB like Pinecone, Weaviate, or Chroma) →](state-17-semantic-storage-vector-db.html)

**Read in this order**

1. [In plain words](#in-plain-words): what it is, without jargon
2. [The problem it solves](#the-problem-it-solves): the problem, and the standard approach in my words
3. [How to implement it (ServiceApps)](#how-to-implement-it-serviceapps): scenario, steps, code and real output
4. [In NurseOps Now](#in-nurseops-now): built or not, and where
5. [Trade-offs](#trade-offs) and [Interview answer](#interview-answer)

## In plain words

Structured storage keeps exact facts in database tables: ticket numbers, statuses, dates, approvals. You ask it precise questions and always get the exact answer, which a meaning-based search can't guarantee.

**In plain terms:** a spreadsheet with fixed columns: you look up row INC0012345 and get exactly that row.

## The problem it solves

**Summarization solves volume, not time**: exact facts need durable storage, and a vector search might return the wrong but similar ticket number.

**The standard approach** (in my words): use SQL for strict facts that need exact retrieval, with deterministic queries.

:::highlight
## How to implement it (ServiceApps)

_Illustrative example: no ServiceApps instance is connected, so the scenario and data are made up. The code is a self-contained sketch; it was run on that made-up data on Nov 19, 2026, and the output below is from that run._

**The setting.** **ServiceApps Assist**, an AI helper inside a company's ServiceApps portal. Employees ask it IT and HR questions; it answers from knowledge-base (KB) articles, looks up the employee's own tickets (incidents like INC0012345) and requests, and keeps one conversation per employee and ticket.

**The scenario.** ServiceApps Assist answers "Which of my tickets are still open, and were any approved?"

**Steps.**

1. Model the facts as tables (tickets, approvals).
2. Let the AI call a tool that runs a fixed, parameterized query, not free-form SQL.
3. Return exact rows to the model.
4. Use Postgres in production; the same SQL works.

**The code** (Python):

```python
import sqlite3
db = sqlite3.connect(":memory:")                 # stand-in for Postgres
db.executescript("""
create table tickets(number text primary key, user text, status text, opened date, priority int);
create table approvals(ticket text references tickets(number), approver text, decision text, at date);
insert into tickets values ('INC0012345','u42','In Progress','2026-11-18',2),
                           ('INC0012346','u42','Resolved','2026-11-02',3),
                           ('INC0012400','u77','New','2026-11-19',1);
insert into approvals values ('INC0012345','mgr9','approved','2026-11-18');
""")
OPEN_TICKETS = """select t.number, t.status, t.opened, a.decision
                  from tickets t left join approvals a on a.ticket = t.number
                  where t.user = ? and t.status != 'Resolved' order by t.opened"""
for row in db.execute(OPEN_TICKETS, ("u42",)):
    print(row)
print(db.execute("select count(*) from tickets where opened >= '2026-11-15'").fetchone()[0], "tickets opened since Nov 15")
```

**Output** (from running the code above):

```
('INC0012345', 'In Progress', '2026-11-18', 'approved')
2 tickets opened since Nov 15
```

**What to watch for.**

- Never let the model write raw SQL against production; give it fixed, parameterized queries as tools.
- Filter by the current user in the query itself, not afterwards.
- Changes to facts should go through code with rules and an audit row.

**In plain terms:** the assistant looks up your ticket by its exact number, like a librarian using a catalog number, not a guess.
:::

## In NurseOps Now

Built on SQLite (Postgres planned for production, per the project's CLAUDE.md): tables `cases`, `ai_reviews`, `decisions`, `audit_log`, `llm_calls`. The AI reads them only through tools like `get_case`. See [Step 4](../nurseops-now-state.html#step-4-hard-state-stays-in-sql).

## Trade-offs

- Exact and reliable, but only for what you modeled as columns.
- Schema changes need migrations.

## Interview answer

"Exact facts like ticket status and approvals go in SQL, and the agent reads them through fixed, parameterized query tools filtered by the user. A vector search might return a similar ticket; SQL returns the right one."

All data in this post is made up. No real people, tickets or patient data.

[← Back to all 27 solutions in the state management blog](../nurseops-now-state.html#how-a-chat-turn-flows-and-where-state-lives)
