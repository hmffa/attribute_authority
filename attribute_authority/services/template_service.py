import os
from jinja2 import Environment, FileSystemLoader

templates_dir = os.path.join(os.path.dirname(__file__), "email_templates")
jinja_env = Environment(loader=FileSystemLoader(templates_dir))

def render_template(template_name: str, context: dict) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(**context)