from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User
from .utils import get_pagination


def index(request):
    """Отображает главную страницу с 10 последними созданными постами."""
    posts = Post.objects.select_related('group',).all()
    page_obj = get_pagination(request, posts)
    context = {
        "page_obj": page_obj,
    }

    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Отображает все посты выбранной категории в порядке убывания по дате."""
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.filter(group=group)
    page_obj = get_pagination(request, posts)
    context = {
        'group': group,
        "page_obj": page_obj,
    }

    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Отображает профиль зарегистрированного пользователя."""
    author = get_object_or_404(User, username=username)
    is_authorized_user = User.objects.filter(
        username=request.user.username
    ).exists()

    posts = Post.objects.select_related(
        'group', 'author'
    ).filter(author=author)
    page_obj = get_pagination(request, posts)
    context = {
        'author': author,
        'page_obj': page_obj,
    }
    if is_authorized_user:
        following = Follow.objects.filter(
            author=author, user=request.user
        ).exists()
        context['following'] = following

    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Отображает выбранный пост."""
    post = get_object_or_404(Post, pk=post_id)
    comments = Comment.objects.filter(post=post.id).select_related('author')
    form = CommentForm()
    context = {
        'post': post,
        'comments': comments,
        'form': form,
    }

    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Отображает форму для создания новой записи."""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()

        return redirect('posts:profile', request.user.username)

    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    """Редактирование выбранного поста."""
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:

        return redirect('posts:post_detail', post.pk)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.method == 'POST' and form.is_valid():
        form.save()

        return redirect('posts:post_detail', post.pk)

    context = {'form': form,
               'is_edit': True,
               'post': post}

    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    """Написание комметариев к постам."""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()

    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Отображает посты авторов из подписок пользователя."""
    user = request.user
    posts = Post.objects.filter(author__following__user=user)
    page_obj = get_pagination(request, posts)
    context = {
        'page_obj': page_obj
    }

    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Подписка на интересного и забавного автора."""
    author = get_object_or_404(User, username=username)
    if request.user != author and not Follow.objects.filter(
        author=author, user=request.user
    ).exists():
        Follow.objects.create(user=request.user, author=author)

    return redirect('posts:profile', author.username)


@login_required
def profile_unfollow(request, username):
    """Отписка от надоеливого или скучного автора."""
    author = get_object_or_404(User, username=username)
    if Follow.objects.filter(user=request.user, author=author).exists():
        Follow.objects.get(user=request.user, author=author).delete()

    return redirect('posts:profile', author.username)
