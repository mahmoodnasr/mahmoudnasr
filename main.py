import os
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from openai import RateLimitError

from crewai import Agent, Task, Process  # Crew not needed for manual loop

# ----------------------------
# Setup
# ----------------------------
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Missing OPENAI_API_KEY. Set it in your env or .env file.")

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_DIR = OUTPUT_DIR / f"run_{RUN_ID}"
RUN_DIR.mkdir(exist_ok=True)


def save_text(filename: str, content: str) -> None:
    (RUN_DIR / filename).write_text(content, encoding="utf-8")


def load_if_exists(filename: str) -> str | None:
    p = RUN_DIR / filename
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


# ----------------------------
# Single MASTER Agent
# ----------------------------
agent = Agent(
    role="Founder Advisory Brand Architect",
    goal="Design and deliver a complete, high-authority consulting brand for mahmoudnasr.io.",
    backstory=(
        "Senior startup advisor, brand strategist, and conversion-focused copywriter. "
        "Founder-first, decisive, avoids buzzwords, delivers publishable assets."
    ),
    llm="gpt-4o-mini",   # safer throughput
    verbose=False,
    allow_delegation=False,
)


# ----------------------------
# Build tasks (with output constraints)
# ----------------------------
def make_tasks():
    constraints_600 = (
        "\n\nOutput constraints:\n"
        "- Max 600 words\n"
        "- Use headings + bullets\n"
        "- No repetition\n"
        "- Do not restate instructions\n"
        "- Be decisive (no Option A/B/C)\n"
    )

    constraints_800 = (
        "\n\nOutput constraints:\n"
        "- Max 800 words\n"
        "- Use headings + bullets\n"
        "- No repetition\n"
        "- Do not restate instructions\n"
        "- Be decisive\n"
    )

    t1 = Task(
        description=(
            "STEP 1 — STRATEGIC POSITIONING\n"
            "Define ONE clear positioning for mahmoudnasr.io.\n"
            "Deliver:\n"
            "- Ideal client profile (who this is for AND who it is NOT for)\n"
            "- One core positioning statement\n"
            "- Key founder pain points and risks\n"
            "- Differentiation logic (why Mahmoud vs alternatives)\n"
            + constraints_600
        ),
        expected_output="A decisive positioning document.",
        agent=agent,
    )

    t2 = Task(
        description=(
            "STEP 2 — ADVISORY FRAMEWORK & OFFERS\n"
            "Design a simple advisory framework and 2–3 offers:\n"
            "1) One-off call\n"
            "2) Short structured sprint\n"
            "3) Ongoing retainer\n"
            "Include boundaries and pricing logic.\n"
            "Must align with Step 1 positioning."
            + constraints_800
        ),
        expected_output="Framework + offers + boundaries + pricing logic.",
        agent=agent,
    )

    t3 = Task(
        description=(
            "STEP 3 — WEBSITE STRUCTURE & UX\n"
            "Deliver:\n"
            "- Sitemap (minimal pages)\n"
            "- Homepage section order (text wireframe)\n"
            "- CTA strategy (primary + secondary)\n"
            "Rule: visitor understands value in 60 seconds.\n"
            "Must align with Step 1 and Step 2."
            + constraints_600
        ),
        expected_output="Sitemap + homepage layout + CTA plan.",
        agent=agent,
    )

    t4 = Task(
        description=(
            "STEP 4 — HOMEPAGE COPY (PUBLISH-READY)\n"
            "Write full homepage copy:\n"
            "- Problem-first hero\n"
            "- Pain articulation\n"
            "- Value proposition\n"
            "- Process\n"
            "- Credibility framing (no bragging)\n"
            "- CTA\n"
            "Tone: calm, confident, human, opinionated.\n"
            "Must align with Step 1–3."
            + constraints_800
        ),
        expected_output="Publish-ready homepage copy.",
        agent=agent,
    )

    t5 = Task(
        description=(
            "STEP 5 — AUTHORITY CONTENT STRATEGY\n"
            "Deliver 10–15 topics for early-stage founders.\n"
            "For each: decision focus, stance/angle (1–2 sentences), and which offer/CTA it points to.\n"
            "Avoid generic advice and SEO bait."
            + constraints_800
        ),
        expected_output="Content roadmap with decision angles + CTA mapping.",
        agent=agent,
    )

    t6 = Task(
        description=(
            "STEP 6 — FINAL INTEGRATION\n"
            "Integrate everything into one cohesive final package:\n"
            "- Final positioning summary\n"
            "- Final offers\n"
            "- Final homepage copy\n"
            "- Content roadmap\n"
            "- Next execution steps\n"
            "Everything must be coherent and decisive."
            + constraints_800
        ),
        expected_output="One cohesive final output package.",
        agent=agent,
    )

    return [t1, t2, t3, t4, t5, t6]


# ----------------------------
# Execute with checkpointing
# ----------------------------
def run_with_checkpoints(tasks):
    outputs = []

    for i, task in enumerate(tasks, start=1):
        checkpoint_name = f"task_{i:02d}.md"

        # Resume if already saved
        existing = load_if_exists(checkpoint_name)
        if existing:
            print(f"✅ Skipping Task {i} (already saved): {checkpoint_name}")
            outputs.append(existing)
            continue

        print(f"\n▶ Running Task {i} ...")

        # Build context from previous outputs (short + safe)
        # Keep context bounded to avoid token spikes.
        context = "\n\n".join(outputs[-3:])  # only last 3 steps as context

        try:
            # Most CrewAI versions support task.execute_sync(agent=..., context=...)
            result = task.execute_sync(agent=agent, context=context)
            text = str(result)

            save_text(checkpoint_name, text)
            outputs.append(text)

            print(f"💾 Saved: {checkpoint_name}")

            # Small pause to reduce burst TPM issues
            time.sleep(1.5)

        except RateLimitError as e:
            # Handles TPM or quota errors
            save_text(f"ERROR_task_{i:02d}.txt", str(e))
            print("\n❌ OpenAI RateLimitError / TPM / quota:")
            print(str(e))
            print(f"Saved error details to: ERROR_task_{i:02d}.txt")
            raise
        except Exception as e:
            save_text(f"ERROR_task_{i:02d}.txt", repr(e))
            print("\n❌ Unexpected error:")
            print(repr(e))
            print(f"Saved error details to: ERROR_task_{i:02d}.txt")
            raise

    # Final combined output
    final = "\n\n---\n\n".join(outputs)
    save_text("FINAL_ALL_STEPS_RAW.md", final)
    print("\n✅ Saved combined output: FINAL_ALL_STEPS_RAW.md")
    return final


def main():
    tasks = make_tasks()
    final = run_with_checkpoints(tasks)
    print(f"\nDone. Outputs in: {RUN_DIR.resolve()}")


if __name__ == "__main__":
    main()