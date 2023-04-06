from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    defaults = {
        'title': 'sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'sample recipe description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com', password='testpass123')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_limited_user(self):
        other_user = create_user(
            email='test1@example.com', password='testpass123')

        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            'title': 'simple recipe title',
            'time_minutes': 22,
            'price': Decimal('5.50'),
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        original_link = 'http://example.com/recipe.pdf'
        recipe = create_recipe(
            title='simple recipe title',
            user=self.user,
            link=original_link
        )

        payload = {
            'title': 'new recipe title',
        }

        url = detail_url(recipe.id)

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        recipe = create_recipe(
            title='simple recipe title',
            user=self.user,
            link='http://example.com/recipe.pdf'
        )

        payload = {
            'title': 'new recipe title',
            'description': 'new recipe description',
            'time_minutes': 23,
            'price': Decimal('6.5'),
            'link': 'http://example.com/recipe.pdf',
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_error(self):
        other_user = create_user(
            email='test2@example.com', password='testpass123')
        recipe = create_recipe(user=self.user)

        payload = {
            'user': other_user.id,
            'title': 'new recipe title',
        }

        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        other_user = create_user(
            email='test3@example.com', password='testpass123')
        recipe = create_recipe(user=other_user)
        url = detail_url(recipe.id)

        res = self.client.delete(url)
        self.assertEquals(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tag(self):
        payload = {
            'title': 'sample recipe title',
            'time_minutes': 20,
            'price': Decimal('4.50'),
            'tags': [{'name': 'karthik'}, {'name': 'perisetti'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            self.assertTrue(recipe.tags.filter(
                user=self.user,
                name=tag['name'],
            ).exists())

    def test_create_recipe_with_existing_tag(self):
        karthik_tag = Tag.objects.create(name='karthik', user=self.user)
        payload = {
            'title': 'sample recipe title',
            'time_minutes': 20,
            'price': Decimal('4.50'),
            'tags': [{'name': 'karthik'}, {'name': 'perisetti'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(karthik_tag, recipe.tags.all())

    def test_create_tag_on_update(self):
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'karthik'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        tag = Tag.objects.get(user=self.user, name='karthik')
        self.assertIn(tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        karthik_tag = Tag.objects.create(name='karthik', user=self.user)
        recipe = create_recipe(user=self.user)
        recipe.tags.add(karthik_tag)

        payload = {'tags': [{'name': 'karthik'}, {'name': 'perisetti'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEquals(recipe.tags.count(), 2)
        tag = Tag.objects.get(user=self.user, name='karthik')
        self.assertIn(tag, recipe.tags.all())
        tag = Tag.objects.get(user=self.user, name='perisetti')
        self.assertIn(tag, recipe.tags.all())

    def test_update_recipe_replace_tag(self):
        karthik_tag = Tag.objects.create(name='karthik', user=self.user)
        recipe = create_recipe(user=self.user)
        recipe.tags.add(karthik_tag)

        payload = {'tags': [{'name': 'perisetti'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEquals(recipe.tags.count(), 1)
        tag = Tag.objects.get(user=self.user, name='karthik')
        self.assertNotIn(tag, recipe.tags.all())
        tag = Tag.objects.get(user=self.user, name='perisetti')
        self.assertIn(tag, recipe.tags.all())

    def test_clear_recipe_tags(self):
        karthik_tag = Tag.objects.create(name='karthik', user=self.user)
        recipe = create_recipe(user=self.user)
        recipe.tags.add(karthik_tag)

        payload = {'tags': []}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.tags.count(), 0)
