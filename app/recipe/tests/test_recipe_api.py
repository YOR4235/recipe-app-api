import tempfile
import os
from decimal import Decimal

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
    Ingredient,
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


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

    """Tests for Ingredients"""

    def test_create_recipe_with_new_ingredient(self):
        payload = {
            'title': 'sample recipe title',
            'time_minutes': 20,
            'price': Decimal('4.50'),
            'ingredients': [{'name': 'karthik'}, {'name': 'perisetti'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            self.assertTrue(recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name'],
            ).exists())

    def test_create_recipe_with_existing_ingredient(self):
        karthik_ingredient = Ingredient.objects.create(
            name='karthik', user=self.user)
        payload = {
            'title': 'sample recipe title',
            'time_minutes': 20,
            'price': Decimal('4.50'),
            'ingredients': [{'name': 'karthik'}, {'name': 'perisetti'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(karthik_ingredient, recipe.ingredients.all())

    def test_create_ingredient_on_update(self):
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'karthik'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        ingredient = Ingredient.objects.get(user=self.user, name='karthik')
        self.assertIn(ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        karthik_ingredient = Ingredient.objects.create(
            name='karthik', user=self.user)
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(karthik_ingredient)

        payload = {'ingredients': [{'name': 'karthik'}, {'name': 'perisetti'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.count(), 2)
        ingredient = Ingredient.objects.get(user=self.user, name='karthik')
        self.assertIn(ingredient, recipe.ingredients.all())
        ingredient = Ingredient.objects.get(user=self.user, name='perisetti')
        self.assertIn(ingredient, recipe.ingredients.all())

    def test_update_recipe_replace_ingredient(self):
        karthik_ingredient = Ingredient.objects.create(
            name='karthik', user=self.user)
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(karthik_ingredient)

        payload = {'ingredients': [{'name': 'perisetti'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.count(), 1)
        ingredient = Ingredient.objects.get(user=self.user, name='karthik')
        self.assertNotIn(ingredient, recipe.ingredients.all())
        ingredient = Ingredient.objects.get(user=self.user, name='perisetti')
        self.assertIn(ingredient, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        karthik_ingredient = Ingredient.objects.create(
            name='karthik', user=self.user)
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(karthik_ingredient)

        payload = {'ingredients': []}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        recipe1 = create_recipe(user=self.user, title='chicken')
        recipe2 = create_recipe(user=self.user, title='mutton')
        recipe3 = create_recipe(user=self.user, title='fish')
        tag1 = Tag.objects.create(user=self.user, name='breakfast')
        tag2 = Tag.objects.create(user=self.user, name='lunch')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)

        payload = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPES_URL, payload)

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_by_ingredients(self):
        recipe1 = create_recipe(user=self.user, title='chicken')
        recipe2 = create_recipe(user=self.user, title='mutton')
        recipe3 = create_recipe(user=self.user, title='fish')
        ingredient1 = Ingredient.objects.create(
            user=self.user, name='chicken rice')
        ingredient2 = Ingredient.objects.create(
            user=self.user, name='mutton rice')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)

        payload = {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        res = self.client.get(RECIPES_URL, payload)

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)


class ImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com', password='testpass123')
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):

        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):

        url = image_upload_url(self.recipe.id)
        payload = {'image': 'badrequest.jpg'}
        res = self.client.post(url, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
