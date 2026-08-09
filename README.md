# AI-Powered HR Automation Suite

A collection of six [n8n](https://n8n.io/) workflows that automate common HR processes end-to-end — from onboarding and leave management to AI-driven resume screening, employee sentiment tracking, and a WhatsApp-based HR assistant. Each workflow combines triggers, Google Sheets as a lightweight data store, OpenAI (GPT-4) for reasoning/extraction tasks, and Slack/Gmail/WhatsApp for notifications and communication.

## Why this project

HR teams juggle a lot of repetitive, time-sensitive tasks — chasing onboarding checklists, approving leave, screening resumes, checking in on employee wellbeing. This suite shows how a handful of automation workflows, glued together with a bit of AI, can take over the repetitive parts and surface only what needs a human decision.

## Workflows

| Workflow | Trigger | What it does |
|---|---|---|
| [`employee-onboarding-automation.json`](workflows/employee-onboarding-automation.json) | Scheduled (every 2 hrs) | Scans upcoming hires in a Google Sheet, calculates which onboarding tasks are due (welcome email, IT setup request, day-1 checklist) based on days until joining, and fires them off automatically while updating status. |
| [`leave-management-system.json`](workflows/leave-management-system.json) | Webhook | Employees submit a leave request in plain language; GPT-4 extracts structured details (dates, type, duration), the workflow checks leave balance, and either auto-approves or routes to the manager for approval via email. |
| [`employee-sentiment-feedback-analyzer.json`](workflows/employee-sentiment-feedback-analyzer.json) | Scheduled (weekly) + Webhook | Sends a weekly one-click mood pulse survey to all active employees, then uses GPT-4 to analyze free-text feedback for sentiment, key themes, and attrition risk — alerting HR on Slack when urgency is high. |
| [`ai-policy-qa-bot.json`](workflows/ai-policy-qa-bot.json) | Webhook | Employees ask HR policy questions in natural language; the workflow pulls all policies from a Google Sheet as context and has GPT-4 answer strictly from that context, logging every query for review. |
| [`ai-resume-screener-ranker.json`](workflows/ai-resume-screener-ranker.json) | Webhook (resume upload) | Extracts text from an uploaded resume PDF, has GPT-4 score the candidate against a role's requirements (experience, skills, education, career progression), saves results to a sheet, and pings Slack for high-scoring candidates. |
| [`whatsapp-hr-chatbot.json`](workflows/whatsapp-hr-chatbot.json) | Webhook (WhatsApp Business API) | Routes incoming WhatsApp messages through GPT-4 to answer common HR questions (leave balance, policies, payslips) conversationally, replying back over WhatsApp. |

## Tech stack

- **Automation engine:** [n8n](https://n8n.io/) (workflow JSON, importable directly)
- **AI/LLM:** OpenAI GPT-4 via the n8n LangChain OpenAI node, for extraction, scoring, and Q&A
- **Data store:** Google Sheets (used as a lightweight, no-setup database for hires, leave balances, policies, candidates, and feedback)
- **Notifications/Comms:** Gmail, Slack, WhatsApp Business API (Meta Graph API)

## Architecture pattern

Most workflows follow the same shape:

```
Trigger (schedule / webhook)
   → Fetch or extract data
   → AI processing (GPT-4: extract / score / analyze / answer)
   → Parse & validate AI response (JS Code node, with fallback on parse failure)
   → Branch on business logic (IF nodes)
   → Persist to Google Sheets
   → Notify (Gmail / Slack / WhatsApp) and/or respond to the original request
```

## Setup

These are n8n workflow exports — to run them you'll need an n8n instance (self-hosted or [n8n Cloud](https://n8n.io/cloud/)).

1. Import a workflow: n8n → **Workflows** → **Import from File** → select a `.json` from [`workflows/`](workflows/).
2. Replace the placeholder credentials referenced in each workflow (`your-google-credential-id`, `your-openai-credential-id`, `your-gmail-credential-id`, `your-slack-credential-id`) with your own, connected in n8n's **Credentials** section.
3. Replace `YOUR_GOOGLE_SHEET_ID` with the ID of your own Google Sheet, and set up the expected tabs/columns (see the **Data model** notes in each workflow's nodes — e.g. `NewHires`, `LeaveBalances`, `LeaveRecords`, `Employees`, `EmployeeFeedback`, `Policies`, `PolicyQueries`, `Candidates`).
4. Replace `YOUR_APP_URL` placeholders with a real endpoint if you're building out approve/reject or feedback-capture pages.
5. For the WhatsApp bot, set the `WHATSAPP_PHONE_ID` environment variable and configure a Meta WhatsApp Business API webhook pointing at the workflow's webhook URL.

> **Note on credentials:** No real API keys, sheet IDs, or tokens are included in these files — every credential and ID is a placeholder for you to fill in with your own.

## Possible extensions

- Swap Google Sheets for a proper database (Postgres/Airtable) as data volume grows
- Add a real approve/reject web page for the leave management manager links
- Extend the resume screener to compare against multiple open roles, not just one hardcoded requirement
- Add authentication to the public webhooks before deploying to production

---
*Built as a portfolio project exploring practical AI + workflow automation for HR use cases.*
