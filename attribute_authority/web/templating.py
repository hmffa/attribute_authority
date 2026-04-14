from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"


class CompatibilityJinja2Templates(Jinja2Templates):
	def TemplateResponse(self, *args: Any, **kwargs: Any):  # type: ignore[override]
		if args and isinstance(args[0], str):
			name = args[0]
			context = args[1] if len(args) > 1 else kwargs.get("context")
			if context is None or "request" not in context:
				raise ValueError("Template context must include a request object")
			return super().TemplateResponse(
				context["request"],
				name,
				context,
				*args[2:],
				**kwargs,
			)
		return super().TemplateResponse(*args, **kwargs)


templates = CompatibilityJinja2Templates(directory=str(TEMPLATES_DIR))