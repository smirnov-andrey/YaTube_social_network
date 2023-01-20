from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()
REDIRECT_URL = '?next='


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='PostAuthor')
        cls.user = User.objects.create_user(username='AnotherUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group',
            description='Тестовая группа для проверки URLs')
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый пост' * 30,)
        cls.names_to_url = (
            # redirect name | args | direct url
            ('posts:index', None,
             '/'),
            ('posts:group_posts', (cls.group.slug,),
             f'/group/{cls.group.slug}/'),
            ('posts:profile', (cls.author.username, ),
             f'/profile/{cls.author.username}/'),
            ('posts:post_detail', (cls.post.pk,),
             f'/posts/{str(cls.post.pk)}/'),
            ('posts:post_create', None,
             '/create/'),
            ('posts:post_edit', (cls.post.pk,),
             f'/posts/{str(cls.post.pk)}/edit/'),
            ('posts:add_comment', (cls.post.pk,),
             f'/posts/{str(cls.post.pk)}/comment/'),
            ('posts:follow_index', None,
             '/follow/'),
            ('posts:profile_follow', (cls.author.username, ),
             f'/profile/{cls.author.username}/follow/'),
            ('posts:profile_unfollow', (cls.author.username, ),
             f'/profile/{cls.author.username}/unfollow/')
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.user_client = Client()
        self.user_client.force_login(self.user)

    def test_post_reverse_name_to_correct_url(self):
        """reverse возвращает соответствующий url"""
        for name, args, url in self.names_to_url:
            with self.subTest(name=name, address=url):
                self.assertEqual(reverse(name, args=args), url,
                                 'reverse возвращает не верный url')

    def test_post_404(self):
        """Проверяем несуществующая страница возвращает 404"""
        response = self.client.get('unexisting_page')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url = (
            # redirect name | args | html template url
            ('posts:index', None, 'posts/index.html'),
            ('posts:group_posts', (self.group.slug,), 'posts/group_list.html'),
            ('posts:profile', (self.author.username,),
             'posts/profile.html'),
            ('posts:post_detail', (self.post.pk,), 'posts/post_detail.html'),
            ('posts:post_create', None, 'posts/create_post.html'),
            ('posts:post_edit', (self.post.pk,), 'posts/create_post.html'),
            ('posts:follow_index', None, 'posts/follow.html'),
        )
        for name, args, template_url in templates_url:
            with self.subTest(name=name, template_url=template_url):
                response = self.author_client.get(
                    reverse(name, args=args))
                self.assertTemplateUsed(
                    response, template_url,
                    'страница использует не верный html шаблон')

    def test_posts_url_access_guest_user(self):
        """URL-адрес доступен неавторизованному пользователю."""
        pages_with_guest_access = (
            'posts:index',
            'posts:group_posts',
            'posts:profile',
            'posts:post_detail',
        )
        for name, args, url in self.names_to_url:
            with self.subTest(name=name):
                if name in pages_with_guest_access:
                    response = self.client.get(reverse(name, args=args))
                    self.assertEqual(response.status_code, HTTPStatus.OK,
                                     'неверный http статус для гостевого '
                                     'пользователя')
                else:
                    response = self.client.get(
                        reverse(name, args=args), follow=True)
                    self.assertRedirects(
                        response, f'''{reverse('auth:login')}{
                        REDIRECT_URL}{reverse(name, args=args)}''')

    def test_posts_url_access_authorised_user(self):
        """URL-адрес дступен неавторизованному пользователю."""
        redirect_urls = {'posts:post_edit':
                         ('posts:post_detail', str(self.post.pk)),
                         'posts:add_comment':
                         ('posts:post_detail', str(self.post.pk)),
                         'posts:profile_follow':
                         ('posts:profile', (self.author.username,)),
                         'posts:profile_unfollow':
                         ('posts:profile', (self.author.username,))
                         }
        for name, args, url in self.names_to_url:
            with self.subTest(name=name):
                if name in redirect_urls.keys():
                    response = self.user_client.get(
                        reverse(name, args=args), follow=True)
                    self.assertRedirects(
                        response,
                        reverse(redirect_urls[name][0],
                                args=redirect_urls[name][1]))
                else:
                    response = self.user_client.get(reverse(name, args=args))
                    self.assertEqual(response.status_code, HTTPStatus.OK,
                                     'неверный http статус для '
                                     'авторизованного пользователя')

    def test_posts_url_access_author(self):
        """URL-адрес дступен автору."""
        redirect_urls = {'posts:add_comment':
                         ('posts:post_detail', str(self.post.pk)),
                         'posts:profile_follow':
                         ('posts:profile', (self.author.username,)),
                         }
        response_404 = ('posts:profile_unfollow',)
        for name, args, url in self.names_to_url:
            with self.subTest(name=name):
                if name in redirect_urls.keys():
                    response = self.author_client.get(
                        reverse(name, args=args), follow=True)
                    self.assertRedirects(
                        response,
                        reverse(redirect_urls[name][0],
                                args=redirect_urls[name][1]))
                else:
                    response = self.author_client.get(reverse(name, args=args))
                    if name in response_404:
                        self.assertEqual(response.status_code,
                                         HTTPStatus.NOT_FOUND,
                                         'неверный http статус для автора'
                                         'должна возвращать 404')
                    else:
                        self.assertEqual(response.status_code, HTTPStatus.OK,
                                         'неверный http статус для автора')

    def test_add_comment_urls(self):
        name = 'posts:add_comment'
        args = (self.post.pk,)
        url = f'/posts/{str(self.post.pk)}/comment/'
        redirect_url = f'/posts/{str(self.post.pk)}/'
        self.assertEqual(reverse(name, args=args), url,
                         'reverse возвращает не верный url')
        response = self.client.get(
            reverse(name, args=args), follow=True)
        self.assertRedirects(
            response, f'''{reverse('auth:login')}{
            REDIRECT_URL}{reverse(name, args=args)}''')
        response = self.author_client.get(
            reverse(name, args=args))
        self.assertRedirects(response, redirect_url)
        response = self.user_client.get(
            reverse(name, args=args), follow=True)
        self.assertRedirects(response, redirect_url)
