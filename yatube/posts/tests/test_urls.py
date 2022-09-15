from http import HTTPStatus

from django.test import TestCase, Client

from ..models import Group, User, Post


class PostURLTests(TestCase):
    """Тесты URLS приложения Posts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test-user')
        cls.not_author = User.objects.create_user(username='test_user2')
        cls.not_author_client = Client()
        cls.not_author_client.force_login(cls.not_author)
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовый текст',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.user
        )

    def test_homepage(self):
        """Проверка доступа главной страницы."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_group_list(self):
        """Проверка доступа к странице с постами группы."""
        response = self.client.get(f'/group/{self.group.slug}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_profile(self):
        """Проверка доступа к странице с профайлом."""
        response = self.client.get(f'/profile/{self.user.username}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_follow(self):
        """Проверка доступа к странице с подписками."""
        response = self.client.get('/follow/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_detail(self):
        """Проверка доступа к странице с подробной информацией о посте."""
        response = self.client.get(f'/posts/{self.post.pk}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_anonymous_post_edit(self):
        """Страница /posts/1/edit/ перенаправит анонимного польщователя
        на страницу логина."""
        response = self.client.get(f'/posts/{self.post.pk}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.pk}/edit/'
        )

    def test_anonymous_post_create(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина."""
        response = self.client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_not_existing_page(self):
        """Проверяет поведение при запросе на несуществующий url"""
        response = self.client.get('/something/must_be/here/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/something/must_be/here/': 'core/404.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_not_author_cant_edit_post(self):
        """URL-адрес проверяет переадресацию не автора поста."""
        response = self.not_author_client.get(f'/posts/{self.post.pk}/edit/')
        self.assertRedirects(response, f'/posts/{self.post.pk}/')

    def test_anonymous_cant_comment_post(self):
        """Страница написания комментариев перенаправит анонимного
        пользователя на страницу логина."""
        response = self.client.get(f'/posts/{self.post.pk}/comment/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.pk}/comment/')

    def test_authorized_user_can_comment_post(self):
        """Страница написания комментариев перенаправит авторизованного
        пользователя на страницу поста."""
        response = self.authorized_client.get(
            f'/posts/{self.post.pk}/comment/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, f'/posts/{self.post.pk}/')
