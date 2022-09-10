from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    """Форма для создания/редактирования поста."""

    class Meta:
        model = Post
        fields = ('text', 'group', 'image')


class CommentForm(forms.ModelForm):
    """Форма для написания комментария к постам."""

    class Meta:
        model = Comment
        fields = ('text', )
