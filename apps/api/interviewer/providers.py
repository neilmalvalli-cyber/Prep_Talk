from __future__ import annotations

import json
import os
import re
import time
import math
from email.utils import parsedate_to_datetime
from typing import Literal

import httpx
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry
from referencing.exceptions import Unresolvable
from pydantic import BaseModel, ConfigDict, Field, field_validator

PROVIDERS = ("groq", "openrouter", "codex")
BASE_URLS = {"groq": "https://api.groq.com/openai/v1", "openrouter": "https://openrouter.ai/api/v1"}
MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,199}$")
AUTOMATIC_MODELS = {"auto", "openrouter/auto", "openrouter/free", "openrouter/fusion"}


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    live_model: str = Field(max_length=200)
    assessment_model: str = Field(max_length=200)
    live_route: str = Field(default="", max_length=100)
    assessment_route: str = Field(default="", max_length=100)
    paid_opt_in: bool = False

    @field_validator("live_model", "assessment_model")
    @classmethod
    def valid_model(cls, value):
        if value and (not MODEL_ID.fullmatch(value) or value in AUTOMATIC_MODELS):
            raise ValueError("Select an explicit valid model ID")
        return value


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    provider: Literal["groq", "openrouter", "codex"]
    revision: int = Field(ge=0)
    providers: dict[Literal["groq", "openrouter", "codex"], ProviderConfig]


class ProviderFailure(Exception):
    def __init__(self, code, message, retry_after=None):
        self.code, self.message, self.retry_after = code, message, retry_after
        super().__init__(message)

    def public(self):
        return {"code": self.code, "message": self.message, "retry_after": self.retry_after}


class Providers:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(30, connect=8), limits=httpx.Limits(max_connections=4))
        self.catalogs = {}
        self.validations = {}
        self.cooldowns = {}
        from .codex_provider import CodexClient
        self.codex = CodexClient()

    def key(self, provider):
        if provider == "codex":
            from .codex_provider import executable
            return bool(executable())
        return os.getenv("GROQ_API_KEY" if provider == "groq" else "OPENROUTER_API_KEY", "")

    def headers(self, provider):
        key = self.key(provider)
        if not key:
            raise ProviderFailure("missing_credentials", f"Configure {'GROQ_API_KEY' if provider == 'groq' else 'OPENROUTER_API_KEY'} on the server.")
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def check_response(self, response):
        if response.is_success:
            return
        code = {401: "authentication", 403: "authentication", 402: "insufficient_credits", 404: "unavailable_model", 429: "rate_limit", 413: "context_overflow", 400: "invalid_request"}.get(response.status_code, "provider_failure")
        retry = response.headers.get("Retry-After")
        if code == "rate_limit":
            try:
                seconds = float(retry) if retry else 60
            except ValueError:
                try:
                    seconds = parsedate_to_datetime(retry).timestamp() - time.time()
                except (ValueError, TypeError, OverflowError):
                    seconds = 60
            seconds = min(86400, max(1, math.ceil(seconds))) if math.isfinite(seconds) else 60
            retry = str(seconds)
            raise ProviderFailure(code, f"The selected AI provider is rate-limited. Wait {seconds} seconds, then resume to retry. If this continues, check the provider account limits or select another model in Settings for a new interview.", retry)
        raise ProviderFailure(code, f"AI provider returned {response.status_code}. Check configuration or retry explicitly.", retry)

    async def catalog(self, provider):
        if provider == "codex":
            from .codex_provider import MODEL
            row = {"id": MODEL, "name": "Luna (Codex subscription)", "structured_outputs": True, "supported_parameters": ["structured_outputs"]}
            self.catalogs[provider] = (time.time(), {MODEL: row})
            return {"models": [row], "fetched_at": time.time(), "pricing_note": "Uses the API host's signed-in Codex subscription allowance. Plan limits apply; this is not unlimited or offline inference."}
        try:
            response = await self.client.get(BASE_URLS[provider]+"/models", headers=self.headers(provider))
            self.check_response(response)
            rows = response.json()["data"]
            # Latest aliases dynamically resolve to another model and cannot
            # satisfy a frozen explicit-model session. Exclude those entries,
            # rather than rejecting the entire otherwise valid live catalog.
            if isinstance(rows, list) and provider == "openrouter":
                rows = [row for row in rows if not (isinstance(row, dict) and isinstance(row.get("id"), str)
                        and (row["id"].startswith("~") or row["id"] in AUTOMATIC_MODELS))]
            if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("id"), str)
                    or not MODEL_ID.fullmatch(row["id"]) or not isinstance(row.get("supported_parameters", []), list) for row in rows):
                raise ValueError("Invalid model catalog")
            result = {"models": [{"id": row["id"], "name": row.get("name", row["id"]), "pricing": row.get("pricing"), "supported_parameters": row.get("supported_parameters", []), "structured_outputs": row["id"] in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"} if provider == "groq" else "structured_outputs" in row.get("supported_parameters", [])} for row in rows], "fetched_at": time.time(), "pricing_note": "Unknown pricing is not zero. Account spending controls remain necessary."}
            self.catalogs[provider] = (result["fetched_at"], {row["id"]: row for row in rows})
            return result
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ProviderFailure("malformed_output", "Provider model catalog was invalid. Retry explicitly; saved settings are unchanged.") from exc
        except httpx.TimeoutException as exc:
            raise ProviderFailure("timeout", "Provider model catalog timed out. Retry explicitly.") from exc
        except httpx.RequestError as exc:
            raise ProviderFailure("network", "Provider catalog unavailable. Check network and try again.") from exc

    async def endpoints(self, model):
        if not MODEL_ID.fullmatch(model):
            raise ValueError("Select a valid explicit model ID")
        try:
            response = await self.client.get(BASE_URLS["openrouter"]+f"/models/{model}/endpoints", headers=self.headers("openrouter"))
            self.check_response(response)
            result = response.json()
            rows = result["data"]["endpoints"]
            if not isinstance(rows, list) or any(not isinstance(row, dict)
                    or not isinstance(row.get("supported_parameters", []), list)
                    or any(row.get(key) is not None and not isinstance(row[key], str)
                           for key in ("provider_name", "tag", "provider_tag")) for row in rows):
                raise ValueError("Invalid downstream endpoints")
            return result
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ProviderFailure("malformed_output", "OpenRouter route catalog was invalid. Retry explicitly.") from exc
        except httpx.TimeoutException as exc:
            raise ProviderFailure("timeout", "OpenRouter route catalog timed out. Retry explicitly.") from exc
        except httpx.RequestError as exc:
            raise ProviderFailure("network", "OpenRouter routes unavailable. Check network and retry explicitly.") from exc

    async def validate(self, provider, config):
        config = ProviderConfig.model_validate(config).model_dump()
        if provider == "codex":
            from .codex_provider import MODEL
            if config["live_model"] != MODEL or config["assessment_model"] != MODEL or config["live_route"] or config["assessment_route"]:
                raise ProviderFailure("invalid_request", "Codex interviews and reviews use Luna with no downstream route.")
            if not self.key(provider):
                raise ProviderFailure("missing_credentials", "Install Codex CLI and sign in with ChatGPT on the API host.")
            return config
        await self.catalog(provider)
        models = self.catalogs[provider][1]
        for purpose in ("live", "assessment"):
            mid = config[purpose+"_model"]
            if mid not in models:
                raise ProviderFailure("unavailable_model", f"Select an available {purpose} model.")
            if purpose == "assessment":
                supported = mid in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"} if provider == "groq" else "structured_outputs" in models[mid].get("supported_parameters", [])
                if not supported:
                    raise ProviderFailure("structured_outputs_unavailable", "Assessment model must support strict structured outputs.")
            if provider == "openrouter":
                route = config[purpose+"_route"]
                if not route:
                    raise ProviderFailure("route_required", "Approve a downstream provider for each OpenRouter model.")
                endpoints = (await self.endpoints(mid))["data"]["endpoints"]
                match = [ep for ep in endpoints if route in {ep.get("provider_name"), ep.get("tag"), ep.get("provider_tag")}]
                if not match:
                    raise ProviderFailure("route_unavailable", "Selected downstream route is not available for this model.")
                if purpose == "assessment" and not any("structured_outputs" in ep.get("supported_parameters", []) for ep in match):
                    raise ProviderFailure("structured_outputs_unavailable", "Approved assessment endpoint lacks structured-output support.")
        if not config["paid_opt_in"]:
            raise ProviderFailure("paid_consent_required", "Approve potentially paid requests before testing or starting. Free pricing is not assumed.")
        return config

    def body(self, snapshot, messages, purpose="live", schema=None):
        provider = snapshot["provider"]
        config = snapshot["config"]
        # Some OpenRouter models require internal reasoning that shares the
        # completion budget. Groq's low-effort 300-token bound truncates those
        # models before their short spoken question is complete.
        live_tokens = 300 if provider == "groq" else 1200
        body = {"model": config[purpose+"_model"], "messages": messages, "max_tokens": live_tokens if purpose == "live" else 2400, "stream": schema is None}
        if provider == "groq" and body["model"].startswith("openai/gpt-oss-"):
            body.update(reasoning_effort="low", include_reasoning=False)
        if provider == "openrouter":
            body["provider"] = {"only": [config[purpose+"_route"]], "allow_fallbacks": False, "require_parameters": True}
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "assessment", "strict": True, "schema": schema}}
        return body

    async def stream(self, snapshot, messages):
        provider = snapshot["provider"]
        if provider == "codex":
            text = await self.codex.complete(messages)
            yield {"text": text, "usage": None, "route": "codex-subscription"}
            return
        if self.cooldowns.get(provider, 0) > time.time():
            raise ProviderFailure("rate_limit", "Wait for the provider retry deadline before trying again.", str(int(self.cooldowns[provider]-time.time())))
        try:
            async with self.client.stream("POST", BASE_URLS[provider]+"/chat/completions", headers=self.headers(provider), json=self.body(snapshot, messages)) as response:
                self.check_response(response)
                count = 0
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        if count == 0:
                            raise ProviderFailure("empty_response", "Provider returned no usable interview text. Retry explicitly.")
                        return
                    try:
                        obj = json.loads(data)
                        if not isinstance(obj, dict):
                            raise TypeError("Expected stream event object")
                        if obj.get("error"):
                            raise ProviderFailure("partial_stream", "Provider interrupted this response. Retry explicitly; displayed text is incomplete.")
                        choices = obj.get("choices", [])
                        if not isinstance(choices, list):
                            raise TypeError("Expected choices array")
                        choice = choices[0] if choices else {}
                        delta = choice.get("delta")
                        if delta is None:
                            delta = {}
                        if not isinstance(delta, dict):
                            raise TypeError("Expected content delta object")
                        content = delta.get("content")
                        if content is not None and not isinstance(content, str):
                            raise TypeError("Expected text content")
                        finish_reason = choice.get("finish_reason")
                        if finish_reason is not None and not isinstance(finish_reason, str):
                            raise TypeError("Expected completion reason text")
                    except (ValueError, IndexError, TypeError, AttributeError) as exc:
                        raise ProviderFailure("malformed_output", "Provider returned an invalid stream.") from exc
                    if content:
                        count += len(content)
                        if count > 8000:
                            raise ProviderFailure("output_limit", "Provider response exceeded the interview output limit.")
                    usage = obj.get("usage") if isinstance(obj.get("usage"), dict) else None
                    if content or usage is not None:
                        yield {"text": content or "", "usage": usage,
                               "route": obj.get("provider") if isinstance(obj.get("provider"), str) else None}
                    if finish_reason not in {None, "stop"}:
                        raise ProviderFailure("incomplete_response", "Provider did not finish a complete interview response. Retry explicitly; displayed text is incomplete.")
                raise ProviderFailure("partial_stream", "Connection ended before response completion. Retry explicitly.")
        except httpx.TimeoutException as exc:
            raise ProviderFailure("timeout", "Provider timed out. Your committed answer is saved.") from exc
        except httpx.RequestError as exc:
            raise ProviderFailure("network", "Provider connection failed. Your answer is saved; use explicit retry.") from exc
        except ProviderFailure as exc:
            if exc.code == "rate_limit":
                try:
                    self.cooldowns[provider] = time.time()+min(86400, max(1, float(exc.retry_after or 60)))
                except ValueError:
                    self.cooldowns[provider] = time.time()+60
            raise

    async def structured(self, snapshot, messages, schema):
        # Schemas come from application code, never candidate/model text. Use an
        # explicit local-only registry: validation must not fetch remote schemas.
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, registry=Registry())
        provider = snapshot["provider"]
        if self.cooldowns.get(provider, 0) > time.time():
            raise ProviderFailure("rate_limit", "Wait for the provider retry deadline before trying again.", str(max(1, math.ceil(self.cooldowns[provider]-time.time()))))
        try:
            if provider == "codex":
                content = await self.codex.complete(messages, schema)
            else:
                response = await self.client.post(BASE_URLS[snapshot["provider"]]+"/chat/completions", headers=self.headers(snapshot["provider"]), json=self.body(snapshot, messages, "assessment", schema))
                self.check_response(response)
                choice = response.json()["choices"][0]
                message = choice["message"]
                if choice.get("finish_reason") not in {None, "stop"} or message.get("refusal"):
                    raise ValueError("Structured response was refused or incomplete")
                content = message["content"]
            if not isinstance(content, str) or len(content.encode("utf-8")) > 65536:
                raise ValueError("Structured content exceeded its bound or was not text")
            def reject_constant(value):
                raise ValueError("Non-finite JSON number")
            result = json.loads(content, parse_constant=reject_constant)
            validator.validate(result)
            return result
        except ProviderFailure as exc:
            if exc.code == "rate_limit":
                self.cooldowns[provider] = time.time()+float(exc.retry_after or 60)
            raise
        except (ValueError, KeyError, IndexError, TypeError, AttributeError, ValidationError, Unresolvable) as exc:
            raise ProviderFailure("malformed_output", "Structured assessment was invalid; factual review remains available.") from exc
        except httpx.TimeoutException as exc:
            raise ProviderFailure("timeout", "Assessment provider timed out; factual review remains available.") from exc
        except httpx.RequestError as exc:
            raise ProviderFailure("network", "Assessment provider unavailable; factual review remains available.") from exc
