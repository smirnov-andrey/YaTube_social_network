import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .. forms import PostForm
from ..models import Group, Post, Comment

User = get_user_model()
REDIRECT_URL = '?next='
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests_create(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm()
        cls.user = User.objects.create_user(username='Voldemort')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group',
            description='Тестовая группа для проверки форм')
        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-group-2',
            description='Тестовая группа для проверки форм')
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост', )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_forms_new_post_create_guest_user(self):
        """при отправке валидной формы со страницы создания поста
        неавторизованным пользователем новая запись в базе данных не
        создается. редирект на логин."""
        form_data = {
            'text': 'Текст из формы создания поста неавторизованным '
                    'пользователем',
            'group': self.group.pk, }
        post_count = Post.objects.count()
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, '/auth/login/?next=/create/')
        self.assertEqual(Post.objects.count(), post_count,
                         'изменилось количество постов')

    def test_forms_new_post_create_authorized_user(self):
        """при отправке валидной формы со страницы создания поста
        неавторизованным пользователем создаётся новая запись в базе данных."""
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
        form_data = {
            'text': 'Текст из формы создания поста авторизованным '
                    'пользователем',
            'group': self.group.pk,
            'image': uploaded, }
        Post.objects.all().delete()
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True)
        self.assertTrue(
            Post.objects.filter(
                text='Текст из формы создания поста авторизованным '
                     'пользователем',
                group=self.group.pk,
                image='posts/small.gif',
            ).exists(),
            'пост не создан'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse(
            'posts:profile', args=[self.user.username]))
        post_object = Post.objects.first()
        self.assertEqual(post_object.text, form_data['text'],
                         'текст не верный')
        self.assertEqual(post_object.group.pk, form_data['group'],
                         'группа не верная')
        self.assertEqual(post_object.author, self.user,
                         'автор не верный')
        self.assertEqual(post_object.image.read(), small_gif,
                         'картинка загрузилась некорректно')
        self.assertEqual(Post.objects.count(), 1,
                         'не изменилось количество постов')

    def test_cant_post_invalid_form(self):
        """проверяем работу влидатора форм для Post"""
        form_data = {
            'text': '',
            'group': self.group.pk, }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True)
        self.assertFormError(
            response,
            'form',
            'text',
            'Обязательное поле.'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
            follow=True)
        self.assertFormError(
            response,
            'form',
            'text',
            'Обязательное поле.'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_forms_new_post_edit_guest_user(self):
        """редактирование постов для гостевых пользователей не достпно."""
        form_data = {
            'text': 'Текст из формы редактирования поста неавторизованным '
                    'пользователем',
            'group': self.group2.pk, }
        post_count = Post.objects.count()
        self.assertEqual(post_count, 1, 'пост не единственный')
        response = self.client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
            follow=True,)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            reverse('auth:login') + REDIRECT_URL
            + reverse('posts:post_edit', args=(self.post.pk,)))
        self.assertEqual(Post.objects.count(), post_count,
                         'изменилось количество постов')

    def test_forms_new_post_edit_authorized_user(self):
        """при редактировании поста автором изменяется запись в
        базе данных."""
        form_data = {
            'text': 'Текст из формы редактирования поста авторизованным '
                    'пользователем',
            'group': self.group2.pk, }
        post_count = Post.objects.count()
        self.assertEqual(post_count, 1, 'пост не единственный')
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
            follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK,
                         'неверный респоз код')
        self.assertRedirects(response, reverse(
            'posts:post_detail', args=(self.post.pk,)))
        post_object = Post.objects.first()
        self.assertEqual(post_object.text, form_data['text'],
                         'текст не изменился')
        self.assertEqual(post_object.group.pk, form_data['group'],
                         'группа не изменилась')
        self.assertEqual(post_object.author, self.post.author,
                         'автор изменился')
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=(self.group.slug,)))
        self.assertEqual(response.status_code, HTTPStatus.OK,
                         'неверный респоз код')
        self.assertEqual(len(response.context['page_obj']), 0,
                         'пагинатор не пустой')
        self.assertEqual(Post.objects.count(), post_count,
                         'изменилось количество постов')

    def test_forms_add_comment_guest(self):
        """проверяем что гости не могут оставлять комментарии."""
        comment_count = Comment.objects.count()
        response = self.client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data={'text': 'новый комментарий', },
            follow=True,)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            reverse('auth:login') + REDIRECT_URL
            + reverse('posts:add_comment', args=(self.post.pk,)))
        self.assertEqual(
            Comment.objects.count(),
            comment_count,
            'неавторизованные пользователи не должны оставлять коментарии')

    def test_forms_add_comment_authorized(self):
        """при отправке валидной формы комментария авторизованным
        пользователем создается запись в базе комментариев."""
        Comment.objects.all().delete()
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data={'text': 'новый комментарий', },
            follow=True)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(self.post.pk,)))
        self.assertEqual(Comment.objects.count(), 1,
                         'новый коммментарий для авторизованного '
                         'пользователя не добавлен')
        comment_object = Comment.objects.first()
        self.assertEqual(comment_object.text, 'новый комментарий',
                         'текст комментария не верный')
        self.assertEqual(comment_object.author, self.user,
                         'автор комментария не верный')
