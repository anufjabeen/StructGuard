import argparse
import asyncio
import json

from app.core.guardrails_engine import GuardrailsEngine


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Run one structured-output generation.")
    parser.add_argument("--input", required=True, help="Natural language source text.")
    parser.add_argument("--schema", default="incident_report", help="Schema name.")
    parser.add_argument("--model", default="ollama/llama3.2:3b", help="Model id.")
    parser.add_argument("--max-attempts", default=3, type=int, help="Maximum retry attempts.")
    args = parser.parse_args()

    engine = GuardrailsEngine()
    result = await engine.generate(
        input_text=args.input,
        schema_name=args.schema,
        model=args.model,
        max_attempts=args.max_attempts,
    )
    print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_main())
