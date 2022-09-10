from http import HTTPStatus

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class PostURLTests(TestCase):
    """Тесты URL приложения about."""

    def setUp(self):
        # Неавторизованный юзер
        self.client = Client()

    def test_ulr_author(self):
        """Проверка доступности к странице об авторе."""
        response = self.client.get(reverse('about:author'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_ulr_tech(self):
        """Проверка доступности к странице о технологиях."""
        response = self.client.get(reverse('about:tech'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_uses_correct_template(self):
        templates_url_names = {
            'about:author': 'about/author.html',
            'about:tech': 'about/tech.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.client.get(reverse(address))
                self.assertTemplateUsed(response, template)
