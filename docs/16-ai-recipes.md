# 16 — AI Recipes

Cookbook for plugging AI into your module. Each recipe is the smallest possible
change.

## Recipe 1 — Enable AI for a new module

1. Create `modules/<name>/ai.py`:

   ```python
   from orbiteus_core.ai import AIModuleConfig, PromptTemplate

   AI = AIModuleConfig(
       enabled=True,
       system_prompt="You are an assistant for {{ tenant.name }}.",
       accessible_models=["<name>.<model>"],
       callable_actions=["<name>.<model>.create"],
       embed_models=["<name>.<model>"],
       suggested_prompts=[
           PromptTemplate(id="default", label="Quick summary"),
       ],
       dashboard=True,
   )
   ```

2. Done. The engine picks it up at `registry.bootstrap()`. `<PromptInput>` and
   `<AIChatPanel>` work for any page rendering models from this module.

## Recipe 2 — Embed a prompt input on a module page

In any module-aware page (or the auto-renderer's form view):

```tsx
import { PromptInput } from "@/orbiteus-ui";

<PromptInput
  scope="module:hr"
  contextHint={{ model: "hr.employee", id: employeeId }}
  placeholder="Ask about this employee…"
/>
```

The widget reads `AIModuleConfig` for the module, builds the RBAC-scoped tool
list, sends to `/api/ai/chat`, streams the response.

## Recipe 3 — Add a callable action as an AI tool

In `modules/<name>/actions.py`:

```python
Action(
    id="hr.timeoff.approve",
    label="Approve time-off",
    keywords=["approve PTO", "approve vacation"],
    category=ActionCategory.EXECUTE,
    target="api",
    target_url="/api/hr/timeoff/{id}/approve",   # POST
    requires_feature="hr.timeoff.approve",
    icon="check",
)
```

In `ai.py`:

```python
callable_actions = ["hr.timeoff.approve", ...]
```

The AI sees a tool `hr_timeoff_approve(id)`. Authorization is enforced by the
underlying endpoint; AI never bypasses RBAC.

## Recipe 4 — Per-record AI summary

Front-end:

```tsx
import { AIChatPanel } from "@/orbiteus-ui";

<AIChatPanel
  scope="record"
  context={{ model: "crm.lead", id }}
  initialPrompt="Summarize the latest activity on this lead."
/>
```

The panel scopes embeddings + tools to the single record by default.

## Recipe 5 — Dynamic dashboard

```tsx
import { AIDashboard } from "@/orbiteus-ui";

<AIDashboard
  scope="module:crm"
  prompt="Weekly revenue by stage for the last 8 weeks"
/>
```

The engine asks the AI for a chart spec, runs `/api/base/aggregate` with the
chosen parameters, renders with recharts.

## Recipe 6 — Tenant-specific system prompt

In `ai.py`:

```python
system_prompt = """
You are an assistant for {{ tenant.name }}.
Always reply in {{ user.locale }}.
Cite source records by their {{ model }}.{id} when answering data questions.
""".strip()
```

Variables come from `RequestContext` and tenant config.

## Recipe 7 — Local fallback (Ollama)

For air-gapped deployments:

```bash
POST /api/ai/credentials
Content-Type: application/json

{ "provider": "ollama", "secret": "n/a", "model_default": "llama3" }
```

Ollama is treated like any other provider; the engine pings the local URL on
credential creation.

## Recipe 8 — Redact PII from prompts

In `ai.py`:

```python
redaction_rules = [
    Redaction(field="email", strategy="mask"),
    Redaction(field="phone", strategy="hash"),
]
```

Applied automatically before any prompt is sent to a remote provider; raw
values stay in the database.

## What you should NOT do

- Don't import `anthropic` / `openai` SDKs in modules. Always use
  `orbiteus_core.ai.providers`.
- Don't log prompts containing PII outside the audit log redaction pipeline.
- Don't pass elevated `RequestContext` to AI tool calls.
- Don't build module-specific chat UIs — extend `<AIChatPanel>` instead.
