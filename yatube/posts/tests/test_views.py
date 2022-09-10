import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django.db.models import FileField
from django.db.models.fields.files import ImageFieldFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ..models import Group, User, Post
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

    def test_home_page_uses_correct_template(self):
        """View функция index получает правильный шаблон."""
        response = self.client.get(reverse('posts:index'))
        self.assertTemplateUsed(response, 'posts/index.html')

    def test_group_list_page_uses_correct_template(self):
        """View функция group_list получает правильный шаблон."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertTemplateUsed(response, 'posts/group_list.html')

    def test_profile_page_uses_correct_template(self):
        """View функция profile получает правильный шаблон."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertTemplateUsed(response, 'posts/profile.html')

    def test_post_detail_page_uses_correct_template(self):
        """View функция post_detail получает правильный шаблон."""
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertTemplateUsed(response, 'posts/post_detail.html')

    def test_post_create_page_uses_correct_template(self):
        """View функция post_create получает правильный шаблон."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_post_edit_page_uses_correct_template(self):
        """View функция post_edit получает правильный шаблон."""
        response = self.client_author.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        self.assertTemplateUsed(response, 'posts/create_post.html')

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
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE], self.latest_post)
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE].id, self.latest_post.id)
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].text, self.latest_post.text
        )
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].group, self.latest_post.group
        )
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].author, self.latest_post.author
        )
        image = ImageFieldFile(
            name=page_obj[FIRST_POST_ON_PAGE].image.name,
            instance=page_obj[FIRST_POST_ON_PAGE],
            field=FileField()
        )
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE].image, image)

    def test_group_list_page_uses_correct_context(self):
        """Тест view-функция group_list использует верный контекст."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        page_obj = response.context.get('page_obj')
        self.assertIsInstance(page_obj, Page)
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE], self.latest_post)
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE].id, self.latest_post.id)
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].text, self.latest_post.text
        )
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].group, self.latest_post.group
        )
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].author, self.latest_post.author
        )
        self.assertEqual(response.context.get('group'), self.group)
        image = ImageFieldFile(
            name=page_obj[FIRST_POST_ON_PAGE].image.name,
            instance=page_obj[FIRST_POST_ON_PAGE],
            field=FileField()
        )
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE].image, image)

    def test_profile_page_uses_correct_context(self):
        """Тест view-функция profile использует верный контекст."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.author})
        )
        page_obj = response.context.get('page_obj', None)
        self.assertIsInstance(page_obj, Page)
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE], self.latest_post)
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE].id, self.latest_post.id)
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].text, self.latest_post.text
        )
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].group, self.latest_post.group
        )
        self.assertEqual(
            page_obj[FIRST_POST_ON_PAGE].author, self.latest_post.author
        )
        self.assertEqual(response.context.get('author'), self.author)
        image = ImageFieldFile(
            name=page_obj[FIRST_POST_ON_PAGE].image.name,
            instance=page_obj[FIRST_POST_ON_PAGE],
            field=FileField()
        )
        self.assertEqual(page_obj[FIRST_POST_ON_PAGE].image, image)

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
