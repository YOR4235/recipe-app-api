from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Tag,
    Recipe,
)

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='test@example.com', password='testpass123'):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagsAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class privateTagsAPITests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        Tag.objects.create(user=self.user, name="karthik")
        Tag.objects.create(user=self.user, name="perisetti")

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        user2 = create_user(email='test1@example.com')
        tag = Tag.objects.create(user=self.user, name="karthik")
        Tag.objects.create(user=user2, name="perisetti")

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        tag = Tag.objects.create(user=self.user, name='karthik')

        payload = {'name': 'perisetti'}

        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        tag = Tag.objects.create(user=self.user, name='karthik')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_filter_assigned_only(self):
        tag1 = Tag.objects.create(name='ing1', user=self.user)
        tag2 = Tag.objects.create(name='ing2', user=self.user)
        recipe = Recipe.objects.create(
            title='recipe1',
            price=Decimal('5.5'),
            time_minutes=5,
            user=self.user,
        )
        recipe.tags.add(tag1)

        payload = {'assigned_only': 1}
        res = self.client.get(TAGS_URL, payload)

        serializer1 = TagSerializer(tag1)
        serializer2 = TagSerializer(tag2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filtered_tags_unique(self):
        tag = Tag.objects.create(name='ing1', user=self.user)
        recipe1 = Recipe.objects.create(
            title='recipe1',
            price=Decimal('5.5'),
            time_minutes=5,
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='recipe2',
            price=Decimal('5.5'),
            time_minutes=5,
            user=self.user,
        )
        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        payload = {'assigned_only': 1}
        res = self.client.get(TAGS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
