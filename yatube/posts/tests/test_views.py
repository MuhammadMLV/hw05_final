import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django.db.models import FileField
from django.db.models.fields.files import ImageFieldFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from .test_forms import ZERO_INDEX
from ..models import Group, User, Post, Follow
from ..constants import (
    POSTS_ON_PAGE, POSTS_ON_SECOND_PAGE, FIRST_POST_ON_PAGE
)
from ..utils import posts_bulk_create

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    """Тесты Views приложения Post."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.author = User.objects.create_user(username='test_author')
        cls.user = User.objects.create_user(username='test_user')
        cls.client_author = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.client_author.force_login(cls.author)
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
        )
        cls.another_group = Group.objects.create(
            title='Секреты',
            slug='nof_found',
        )
        cls.post = Post.objects.create(
            text='Тестовый',
            author=cls.author,
            group=cls.group,
            image=uploaded
        )
        cls.posts = posts_bulk_create(
            'test text', cls.author, cls.group, uploaded
        )
        cls.latest_post = Post.objects.all()[FIRST_POST_ON_PAGE]

        cls.image = ImageFieldFile(
            name='posts/small.gif',
            instance=cls.latest_post,
            field=FileField(),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def get_first_post_on_page(self, page_obj):
        return page_obj[FIRST_POST_ON_PAGE]

    def check_post(self, page_obj):
        post = self.get_first_post_on_page(page_obj)
        self.assertEqual(post, self.latest_post)
        self.assertEqual(post.id, self.latest_post.id)
        self.assertEqual(post.text, self.latest_post.text)
        self.assertEqual(post.group, self.latest_post.group)
        self.assertEqual(post.author, self.latest_post.author)
        self.assertEqual(post.image, self.latest_post.image)

    def test_pages_uses_correct_templates(self):
        """Страницы используют правильные шаблоны."""
        urls_to_check = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
                'posts/create_post.html',
        }
        for url, template in urls_to_check.items():
            with self.subTest(url=url):
                response = self.client_author.get(url)
                self.assertTemplateUsed(response, template)

    def test_post_detail_page_uses_correct_context(self):
        """View функция post_detail использует верный контекст."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}
                    )
        )
        form_fields = {
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

        context = response.context
        self.assertEqual(context.get('post'), self.post)
        self.assertEqual(context.get('post').id, self.post.id)
        self.assertEqual(context.get('post').text, self.post.text)
        self.assertEqual(context.get('post').group, self.post.group)
        self.assertEqual(context.get('post').author, self.post.author)
        self.assertEqual(context.get('post').image, self.image)

    def test_post_create_page_uses_correct_context(self):
        """View функция post_create использует верный контекст."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_uses_correct_context(self):
        """View функция post_edit использует верный контекст."""
        response = self.client_author.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        is_edit = True
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context.get('is_edit'), is_edit)
        self.assertEqual(response.context.get('post'), self.post)

    def test_paginator(self):
        """Тестируем пагинацию на страницах."""
        urls_to_check = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.author}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        ]
        for url in urls_to_check:
            response = self.client.get(url)
            context = response.context
            with self.subTest(url=url):
                page_obj = context.get('page_obj')
                self.assertEqual(len(page_obj), POSTS_ON_PAGE)

        for url in urls_to_check:
            response = self.client.get(url + '?page=2')
            context = response.context
            with self.subTest(url=url):
                page_obj = context.get('page_obj')
                self.assertIsNotNone(len(page_obj), POSTS_ON_SECOND_PAGE)

    def test_post_not_in_alien_group(self):
        """Тест на отсутствие поста в неправильной группе."""
        response = self.client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.another_group.slug}
            )
        )
        page_obj = response.context.get('page_obj')
        self.assertNotIn(self.post, page_obj)

    def test_index_page_uses_correct_context(self):
        """Тест view-функция index использует верный контекст."""
        response = self.client.get(reverse('posts:index'))
        page_obj = response.context.get('page_obj')
        self.assertIsInstance(page_obj, Page)
        self.check_post(page_obj)

    def test_group_list_page_uses_correct_context(self):
        """Тест view-функция group_list использует верный контекст."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        page_obj = response.context.get('page_obj')
        self.assertIsInstance(page_obj, Page)
        self.assertEqual(response.context.get('group'), self.group)
        self.check_post(page_obj)

    def test_profile_page_uses_correct_context(self):
        """Тест view-функция profile использует верный контекст."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.author})
        )
        page_obj = response.context.get('page_obj', None)
        self.assertIsInstance(page_obj, Page)
        self.assertEqual(response.context.get('author'), self.author)
        self.check_post(page_obj)

    def test_new_post_located_on_first_position(self):
        """Тест проверка на наличие поста на первой позиции на главной
        странице, группы и профиля."""
        new_post = Post.objects.create(
            text='Новый пост',
            author=self.author,
            group=self.group,
        )
        urls_to_check = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.author}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        ]
        for url in urls_to_check:
            response = self.client_author.get(url)
            with self.subTest(url=url):
                page_obj = response.context.get('page_obj')
                self.assertEqual(page_obj[FIRST_POST_ON_PAGE], new_post)


class CacheTest(TestCase):
    """Тест на проверку работы кэширования."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
        )
        cls.INDEX = reverse('posts:index')

    def test_cache(self):
        """Проверяет работоспособность кэша."""
        response_1 = self.authorized_client.get(self.INDEX)
        Post.objects.create(
            text='Новый тестовый текст',
            author=self.user,
        )
        response_2 = self.authorized_client.get(self.INDEX)
        self.assertEqual(
            response_1.content,
            response_2.content
        )
        cache.clear()
        response_3 = self.authorized_client.get(self.INDEX)
        self.assertNotEqual(
            response_1.content,
            response_3.content
        )


class FollowTestCase(TestCase):
    """Тест на проверку работы подписок."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.following_1 = User.objects.create_user(username='famous_user_1')
        cls.following_2 = User.objects.create_user(username='famous_user_2')
        cls.user = User.objects.create_user(username='test_user')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        Follow.objects.create(user=cls.user, author=cls.following_1)
        cls.post_1 = Post.objects.create(
            text='Пост посвящается подсписчику', author=cls.following_1
        )
        cls.post_2 = Post.objects.create(
            text='Пост посвящается автору', author=cls.following_2
        )

    def test_authorized_user_can_follow(self):
        """Проверяет возможность подписки на известного автора."""
        follow = Follow.objects.filter(
            user=self.user, author=self.following_2
        ).exists()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.following_2.username}
            )
        )
        follow_upd = Follow.objects.filter(
            user=self.user, author=self.following_2
        ).exists()
        self.assertNotEqual(follow, follow_upd)

    def test_authorized_user_can_unfollow(self):
        """Проверяет возможность отписки от скучного автора."""
        follow = Follow.objects.filter(
            user=self.user, author=self.following_1
        ).exists()
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.following_1.username}
            )
        )
        follow_upd = Follow.objects.filter(
            user=self.user, author=self.following_1
        ).exists()
        self.assertNotEqual(follow, follow_upd)

    def test_follower_sees_following_author_posts(self):
        """Подписчик видит посты избранных авторов."""
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(self.post_1, response.context.get('page_obj'))

    def test_follower_not_sees_stranger_posts(self):
        """В список избранных не попадают посты незнакомых авторов."""
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post_2, response.context.get('page_obj'))
