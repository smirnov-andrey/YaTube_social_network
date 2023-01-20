from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, Comment, Follow

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower = User.objects.create_user(username='PostAuthor')
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост' * 30,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='текст комментария'
        )
        cls.follow = Follow.objects.create(
            user=cls.follower,
            author=cls.user
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        with self.subTest(model='Group'):
            self.assertEqual(self.group.title, str(PostModelTest.group),
                             '__str__ группы работает не верно')
            self.assertEqual(self.post.text[:15], str(PostModelTest.post),
                             '__str__ поста работает не верно')

    def test_models_have_correct_verbose_names(self):
        group = PostModelTest.group
        field_verboses = {
            'title': 'Название группы',
            'slug': 'Уникальная ссылка',
            'description': 'Описание группы', }
        for field, expected_value in field_verboses.items():
            with self.subTest(model='Group', field=field):
                self.assertEqual(
                    group._meta.get_field(field).verbose_name, expected_value)

        group = PostModelTest.post
        field_verboses = {
            'text': 'Текст поста',
            'pub_date': 'Дата публикации',
            'author': 'Автор поста',
            'group': 'Группа', }
        for field, expected_value in field_verboses.items():
            with self.subTest(model='Post', field=field):
                self.assertEqual(
                    group._meta.get_field(field).verbose_name, expected_value)
        comment = PostModelTest.comment
        field_verboses = {
            'post': 'Пост для комментария',
            'author': 'Автор комментария',
            'text': 'Текст комментария',
            'created': 'Дата публикации комментария',
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(model='Comment', field=field):
                self.assertEqual(
                    comment._meta.get_field(field).verbose_name,
                    expected_value)
        follow = PostModelTest.follow
        field_verboses = {
            'user': 'Пользователь',
            'author': "Автор на которого подписан пользователь",
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(model='Follow', field=field):
                self.assertEqual(
                    follow._meta.get_field(field).verbose_name,
                    expected_value)

    def test_models_have_correct_help_text(self):
        group = PostModelTest.group
        field_help_texts = {
            'title': '',
            'slug': '',
            'description': '', }
        for field, expected_value in field_help_texts.items():
            with self.subTest(model='Group', field=field):
                self.assertEqual(
                    group._meta.get_field(field).help_text, expected_value)

        post = PostModelTest.post
        field_help_texts = {
            'text': 'Введите текст поста',
            'pub_date': '',
            'author': '',
            'group': 'Группа, к которой будет относиться пост', }
        for field, expected_value in field_help_texts.items():
            with self.subTest(model='Post', field=field):
                self.assertEqual(
                    post._meta.get_field(field).help_text, expected_value)
        comment = PostModelTest.comment
        with self.subTest(model='Comment', field='text'):
            self.assertEqual(
                comment._meta.get_field('text').help_text, 'Текст комментария')
