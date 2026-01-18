"""Template manager for loading and rendering slide templates."""

from pathlib import Path


class TemplateManager:
    """Manages HTML slide templates."""

    def __init__(self, template_dir: Path | None = None):
        """Initialize the template manager.

        Args:
            template_dir: Path to template directory (defaults to src/templates)
        """
        if template_dir is None:
            # Get the src/templates directory
            current_file = Path(__file__)
            src_dir = current_file.parent.parent
            template_dir = src_dir / "templates"

        self.template_dir = template_dir
        self.html_dir = template_dir / "html"
        self.css_dir = template_dir / "css"

    def load_template(self, template_name: str) -> str:
        """Load an HTML template.

        Args:
            template_name: Name of the template (e.g., 'title_slide')

        Returns:
            Template HTML content
        """
        template_path = self.html_dir / f"{template_name}.html"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        return template_path.read_text(encoding="utf-8")

    def load_css(self, css_name: str) -> str:
        """Load a CSS file.

        Args:
            css_name: Name of the CSS file (e.g., 'title')

        Returns:
            CSS content
        """
        css_path = self.css_dir / f"{css_name}.css"
        if not css_path.exists():
            raise FileNotFoundError(f"CSS file not found: {css_path}")

        return css_path.read_text(encoding="utf-8")

    def render_title_slide(
        self,
        title: str,
        subtitle: str = "",
        year: str = "",
        tagline: str = "",
        footer: str = "",
    ) -> str:
        """Render a title slide from template.

        Args:
            title: Main title text
            subtitle: Subtitle text
            year: Year text
            tagline: Tagline text
            footer: Footer text

        Returns:
            Rendered HTML
        """
        template = self.load_template("simple_title")

        # Replace content placeholders
        replacements = {
            "{{TITLE_TEXT}}": title,
            "{{SUBTITLE_TEXT}}": subtitle,
            "{{YEAR_TEXT}}": year,
            "{{TAGLINE_TEXT}}": tagline,
            "{{FOOTER_TEXT}}": footer,
        }

        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)

        return template

    def render_ending_slide(
        self,
        links_html: str = "",
    ) -> str:
        """Render an ending slide from template.

        Args:
            links_html: HTML for links section

        Returns:
            Rendered HTML
        """
        template = self.load_template("simple_ending")

        # Replace content placeholders
        template = template.replace("{{LINKS_HTML}}", links_html)

        return template

    def render_content_slide(
        self,
        title: str,
        body: str,
        header_logo_html: str = "",
        footer_html: str = "",
    ) -> str:
        """Render a content slide from template.

        Args:
            title: Slide title
            body: Slide body HTML
            header_logo_html: HTML for header logo
            footer_html: HTML for footer

        Returns:
            Rendered HTML
        """
        template = self.load_template("content_base")
        css = self.load_css("content")

        # Replace CSS placeholder
        template = template.replace("{{CSS}}", css)

        # Replace content placeholders
        replacements = {
            "{{TITLE}}": title,
            "{{BODY}}": body,
            "{{HEADER_LOGO_HTML}}": header_logo_html,
            "{{FOOTER_HTML}}": footer_html,
        }

        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)

        return template
