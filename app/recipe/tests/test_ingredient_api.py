from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe,
)

from recipe.serializers import IngredientSerializer


INGREDIENT_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='test@example.com', password='test123'):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientAPITests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        Ingredient.objects.create(name='ing1', user=self.user)
        Ingredient.objects.create(name='ing2', user=self.user)

        res = self.client.get(INGREDIENT_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retieve_limited_user(self):
        other_user = create_user(email='test2@example.com')
        Ingredient.objects.create(name='ing1', user=self.user)
        Ingredient.objects.create(name='ing2', user=other_user)

        res = self.client.get(INGREDIENT_URL)
        ingredients = Ingredient.objects.filter(
            user=self.user).order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_update_ingredient(self):
        ingredient = Ingredient.objects.create(name='ing1', user=self.user)
        payload = {'name': 'ingg1'}

        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertIn(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        ingredient = Ingredient.objects.create(name='ing1', user=self.user)

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())

    def test_filter_assigned_only(self):
        ingredient1 = Ingredient.objects.create(name='ing1', user=self.user)
        ingredient2 = Ingredient.objects.create(name='ing2', user=self.user)
        recipe = Recipe.objects.create(
            title='recipe1',
            price=Decimal('5.5'),
            time_minutes=5,
            user=self.user,
        )
        recipe.ingredients.add(ingredient1)

        payload = {'assigned_only': 1}
        res = self.client.get(INGREDIENT_URL, payload)

        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filtered_ingredients_unique(self):
        ingredient = Ingredient.objects.create(name='ing1', user=self.user)
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
        recipe1.ingredients.add(ingredient)
        recipe2.ingredients.add(ingredient)

        payload = {'assigned_only': 1}
        res = self.client.get(INGREDIENT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
