from django.contrib.auth import get_user_model
from django.db import models

from .validators import validate_not_empty

User = get_user_model()


class Group(models.Model):
    title = models.CharField(
        verbose_name="Название группы",
        max_length=200)
    slug = models.SlugField(
        verbose_name="Уникальная ссылка",
        max_length=50,
        unique=True)
    description = models.TextField(
        verbose_name="Описание группы")

    class Meta:
        ordering = ("title",)
        verbose_name = "Группа постов"
        verbose_name_plural = "Группы постов"

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(
        verbose_name="Текст поста",
        validators=[validate_not_empty],
        help_text='Введите текст поста')
    pub_date = models.DateTimeField(
        verbose_name="Дата публикации",
        auto_now_add=True,
        db_index=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name="Автор поста")
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        verbose_name="Группа",
        help_text='Группа, к которой будет относиться пост')
    image = models.ImageField(
        verbose_name='Картинка',
        upload_to='posts/',
        blank=True,
        help_text='Загрузите картинку к посту')

    class Meta:
        ordering = ("-pub_date",)
        verbose_name = "Пост"
        verbose_name_plural = "Посты"

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Пост для комментария")
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Автор комментария")
    text = models.TextField(
        verbose_name="Текст комментария",
        validators=[validate_not_empty],
        help_text='Текст комментария')
    created = models.DateTimeField(
        verbose_name="Дата публикации комментария",
        auto_now_add=True,
        db_index=True)

    class Meta:
        ordering = ("-created",)
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self):
        return self.text[:15]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Пользователь')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name="Автор на которого подписан пользователь")

    class Meta:
        ordering = ("user",)
        verbose_name = "Подписчика"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                name="unique_relationships",
                fields=["user", "author"],
            ),
            models.CheckConstraint(
                name="prevent_self_follow",
                check=~models.Q(user=models.F("author")),
            ),
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
