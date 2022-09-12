import http
import shutil
import tempfile

from django.db.models.fields.files import FileField, ImageFieldFile
from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from ..models import Group, Post, User, Comment

COUNT_OF_NEW_ELEMENT = 1
ZERO_INDEX = 0
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    """Проверка работы форм приложения Post."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.client_user = Client()
        cls.client_user.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
        )
        cls.new_group = Group.objects.create(
            title='Новая группа',
            slug='new_group',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.user,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_new_post(self):
        """Тест валидная форма создает новую запись."""
        posts = list(Post.objects.values_list('id', flat=True))
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
        expected_count = len(posts) + COUNT_OF_NEW_ELEMENT
        form_data = {
            'text': 'Текст для новой записи',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.client_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        posts_upd = Post.objects.exclude(id__in=posts)
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.user.username}
            )
        )
        self.assertEqual(Post.objects.count(), expected_count)

        new_post = posts_upd[ZERO_INDEX]
        image = ImageFieldFile(
            name='posts/small.gif',
            instance=new_post,
            field=FileField(),
        )
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group, self.group)
        self.assertEqual(new_post.author, self.user)
        self.assertEqual(new_post.image, image)

    def test_edit_post(self):
        """Тест валидная форма редактирует существующий пост."""
        form_data = {
            'text': 'Текст для новой записи ред.',
            'group': self.new_group.id,
        }
        response = self.client_user.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            )
        )
        self.post.refresh_from_db()
        self.assertEqual(self.post.text, form_data['text'])
        self.assertEqual(self.post.group, self.new_group)
        self.assertEqual(self.post.author, self.user)

    def test_comment(self):
        """Тест валидная форма добавляет комментарий к посту."""
        comments_count = self.post.comments.count()
        expected_count = comments_count + COUNT_OF_NEW_ELEMENT
        form_data = {
            'text': 'Тестовый комментарий для поста'
        }
        self.client_user.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(self.post.comments.count(), expected_count)
