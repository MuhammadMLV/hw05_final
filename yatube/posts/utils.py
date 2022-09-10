from django.core.paginator import Paginator

from .constants import POSTS_ON_PAGE, POSTS_FOR_PAGINATOR
from .models import Post


def get_pagination(request, posts):
    """Формирует пагинацию для постов."""
    paginator = Paginator(posts, POSTS_ON_PAGE)
    page_number = request.GET.get('page')

    return paginator.get_page(page_number)


def posts_bulk_create(
        text, author, group, image, quantity=POSTS_FOR_PAGINATOR):
    """Создает заданное количество постов с указанным текстом, группой,
    и автором."""
    posts = (
        Post(
            text=text + str(i),
            author=author,
            group=group,
            image=image
        ) for i in range(quantity)
    )

    return Post.objects.bulk_create(posts)
