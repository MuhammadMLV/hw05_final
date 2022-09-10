from django.views.generic.base import TemplateView


class AboutAuthorView(TemplateView):
    """Отображает страницу 'Об авторе проекта'."""

    template_name = 'about/author.html'


class AboutTechView(TemplateView):
    """Отображает страницу 'Технологии'."""

    template_name = 'about/tech.html'
