from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Voldemort')

    def test_cache_index(self):
        """проверяем работу кеша для страницы index"""
        group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group',
            description='Тестовая группа 1 для проверки')
        Post.objects.create(
            author=self.user,
            group=group,
            text='Тестовый пост' * 30,)
        first_response = self.client.get(reverse('posts:index'))
        self.assertEqual(
            len(first_response.context['page_obj']), 1,
            'пост для тестирования не создан')
        Post.objects.all().delete()
        cached_response = self.client.get(reverse('posts:index'))
        self.assertEqual(
            cached_response.content, first_response.content,
            'контента в кеше не сохранился после удаления поста')
        cache.clear()

        clear_cache_response = self.client.get(reverse('posts:index'))
        self.assertNotEqual(
            cached_response.content, clear_cache_response.content,
            'конттент не изменился после очистки кеша')
