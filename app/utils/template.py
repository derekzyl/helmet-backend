from typing import Any

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

templates = Jinja2Templates(directory="templates")


def renderTemplate(directory: str, data: dict[str, Any]):
    """
    The function `renderTemplate` takes a directory and data as input, loads a template from the
    specified directory, renders the template with the provided data, and returns the rendered template
    content.

    :param directory: The `directory` parameter is a string that represents the path to the template
    file. It specifies the location of the template file within the templates directory
    :type directory: str
    :param data: The `data` parameter is a dictionary that contains the data to be passed to the
    template. The keys in the dictionary represent the variable names in the template, and the values
    represent the values to be assigned to those variables
    :type data: dict[str, Any]
    :return: the rendered content of the template.
    """
    # return templates.(name="verify_email.html", context=data)

    template_env = Environment(loader=FileSystemLoader("templates"))
    template = template_env.get_template(directory)
    template_content = template.render(**data)
    return template_content
