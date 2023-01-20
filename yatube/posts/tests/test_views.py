import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django import forms

from ..forms import PostForm
from ..models import Group, Post, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()
BULK_POSTS_COUNT = 13


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Voldemort')
        cls.follower = User.objects.create_user(username='HarryPotter')
        Follow.objects.create(
            user=cls.follower,
            author=cls.author
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group',
            description='Тестовая группа 1 для проверки')
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый пост' * 30,
            image=uploaded,)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)

    def content_test(self, response, post_check=False, group_check=False,
                     author_check=False):
        if post_check:
            post_object = response.context['post']
        else:
            post_object = response.context['page_obj'][0]
        tests_data = (
            # test_object | expected_result | message
            (post_object.text, self.post.text, 'текст поста не совпадает'),
            (post_object.pub_date, self.post.pub_date, 'дата поста не '
                                                       'совпадает'),
            (post_object.author, self.post.author, 'автор поста не совпадает'),
            (post_object.group, self.post.group, 'группа поста не совпадает'),
            (post_object.image, self.post.image, 'картинка поста не '
                                                 'передается')
        )
        for test_object, expected_result, message in tests_data:
            with self.subTest(test_object=test_object):
                self.assertEqual(test_object, expected_result, message)
        if group_check:
            with self.subTest(test_object='group'):
                self.assertEqual(response.context['group'], self.group,
                                 'группа на странице group_posts не совпадает')
        if author_check:
            with self.subTest(test_object='author'):
                self.assertEqual(response.context['author'], self.author,
                                 'автор на странице profile не совпадает')

    def test_post_views_show_correct_context(self):
        """Шаблон сформирован с правильным контекстом."""
        page_names = (
            # name | args | post_check | group_check | author_check
            ('posts:index', None, False, False, False),
            ('posts:group_posts', (self.group.slug,), False, True, False),
            ('posts:profile', (self.author.username,), False, False, True),
            ('posts:post_detail', (self.post.pk,), True, False, False),
            ('posts:follow_index', None, False, False, False),
        )
        for (reverse_name, reverse_args, post_check, group_check,
             author_check) in page_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.follower_client.get(
                    reverse(reverse_name, args=reverse_args))
                self.content_test(response, post_check, group_check,
                                  author_check)

    def test_post_views_show_correct_forms(self):
        """Шаблон сформирован с правильными формами."""
        page_names = (
            ('posts:post_create', None),
            ('posts:post_edit', (self.post.pk,))
        )
        expected_form_fields = (
            ('text', forms.fields.CharField),
            ('group', forms.fields.ChoiceField),
            ('image', forms.fields.ImageField)
        )
        for reverse_name, reverse_args in page_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse(
                    reverse_name, args=reverse_args))
                self.assertIn('form', response.context)
                self.assertIsInstance(response.context.get('form'), PostForm)
                for field_name, field_type in expected_form_fields:
                    with self.subTest(expected_field=field_type):
                        form_field = response.context.get(
                            'form').fields.get(field_name)
                        self.assertIsInstance(form_field, field_type)

    def test_post_exist_in_group(self):
        """Пост отбражаетя в провильной группе"""
        Post.objects.all().delete()
        self.post = Post.objects.create(
            author=self.author,
            group=self.group,
            text='Тестовый пост 2' * 30, )
        group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-group-2',
            description='Тестовая группа 2 для проверки')
        response = self.author_client.get(
            reverse('posts:group_posts', args=(group2.slug,)))
        self.assertEqual(
            len(response.context['page_obj']), 0,
            'во второй групе количество постов не равно 0')
        self.assertEqual(self.post.group, self.group)
        response = self.author_client.get(
            reverse('posts:group_posts', args=(self.group.slug,)))
        self.assertEqual(
            len(response.context['page_obj']), 1,
            'в первой группе нет поста')

    def test_post_views_paginator(self):
        """Тестирование паджинатора."""
        Post.objects.all().delete()
        Post.objects.bulk_create([
            Post(text=f'Тестовый пост #{post_object_id}',
                 author=self.author,
                 group=self.group,
                 ) for post_object_id in range(BULK_POSTS_COUNT)])
        pages_names = (
            ('posts:index', None),
            ('posts:group_posts', (self.group.slug,)),
            ('posts:profile', (self.author.username,)),
            ('posts:follow_index', None)
        )
        page_numbers = (
            ('', settings.POSTS_ON_PAGE),
            ('?page=2', BULK_POSTS_COUNT - settings.POSTS_ON_PAGE)
        )
        for page_name, args in pages_names:
            with self.subTest(page_name=page_name):
                for url, post_count in page_numbers:
                    with self.subTest(url=url, post_count=post_count):
                        response = self.follower_client.get(
                            reverse(page_name, args=args) + url)
                        self.assertEqual(
                            len(response.context['page_obj']), post_count,
                            'пагинатор отображает неверное количество постов')

    def test_post_follow_index(self):
        """тестируем работу follow_index. Страница доступна только
        поьлзователям кто подписан на автора(ов)"""
        Follow.objects.all().delete()
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertEqual(
            len(response.context['page_obj']), 0,
            'пост не должен отображаться на follow_index если нет подписки')
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.follower_client.get(reverse('posts:follow_index'))
        post_object = response.context['page_obj'][0]
        self.assertEqual(
            len(response.context['page_obj']), 1,
            'пост не отображается на follow_index'
        )
        self.assertEqual(post_object.text, self.post.text,
                         'текст поста не совпадает')
        self.assertEqual(post_object.group, self.post.group,
                         'группа поста не совпадает')
        self.assertEqual(post_object.author, self.post.author,
                         'автор поста не совпадает')
        self.assertEqual(post_object.pub_date, self.post.pub_date,
                         'дата публикации поста не совпадаетт')

    def test_post_follow(self):
        """проверяем работу подписки на автора."""
        Follow.objects.all().delete()
        self.follower_client.post(
            reverse('posts:profile_follow', args=(self.follower.username,)),
            data={'username': self.follower.username},
            follow=True)
        follow_objects = Follow.objects.all()
        self.assertEqual(
            len(follow_objects), 0,
            'функция не должна давать подписаться на самого себя'
        )
        self.follower_client.post(
            reverse('posts:profile_follow', args=(self.author.username,)),
            data={'username': self.author.username},
            follow=True)
        self.follower_client.post(
            reverse('posts:profile_follow', args=(self.author.username,)),
            data={'username': self.author.username},
            follow=True)
        follow_objects = Follow.objects.first()
        self.assertTrue(
            follow_objects,
            'пост не отображается на follow_index'
        )
        self.assertNotEqual(
            Follow.objects.count(), 2,
            'не работает защита от повторной подписки'
        )
        self.assertEqual(
            follow_objects.user, self.follower,
            'пользователь в подписке не совпадает'
        )
        self.assertEqual(
            follow_objects.author, self.author,
            'автор в подписке не совпадает'
        )

    def test_post_unfollow(self):
        """проверяем работу отписки от автора."""
        Follow.objects.all().delete()
        Follow.objects.create(user=self.follower, author=self.author)
        follower_count = Follow.objects.count()
        self.follower_client.post(
            reverse('posts:profile_unfollow', args=(self.author.username,)),
            data={'username': self.author.username},
            follow=True)
        self.assertNotEqual(
            Follow.objects.count(), follower_count,
            'подписка не удалилась'
        )
