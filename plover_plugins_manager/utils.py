from pygments.formatters import HtmlFormatter
import readme_renderer.markdown
import readme_renderer.rst
import readme_renderer.txt


_RENDERERS = {
    None: readme_renderer.rst,
    "": readme_renderer.rst,
    "text/plain": readme_renderer.txt,
    "text/x-rst": readme_renderer.rst,
    "text/markdown": readme_renderer.markdown,
}

_CSS = '\n'.join((
    '<style type="text/css">',
    'pre { background-color: #eeeeee }',
    HtmlFormatter().get_style_defs(),
    '</style>',
))


def description_to_html(content, content_type):
    renderer = _RENDERERS.get(content_type, readme_renderer.rst)
    rendered = renderer.render(content)
    if rendered is None:
        rendered = readme_renderer.txt.render(content)
    return _CSS, rendered
