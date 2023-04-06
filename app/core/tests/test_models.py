from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


def create_user(email='test@example.com', password='testpass123'):
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):

    def test_create_user_with_email_success(self):
        email = "test@example.com"
        password = "test@123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        sample_emails = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@ExampLe.com", "Test2@example.com"],
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, "sample123")
            self.assertEqual(user.email, expected)

    def test_new_user_email_empty(self):
        with self.assertRaises(ValueError):
            get_user_model().objects \
                .create_user(email='', password='simple123')

    def test_create_superuser(self):
        email = "test@example.com"
        password = "test@123"
        user = get_user_model().objects.create_superuser(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        user = get_user_model().objects.create_user(
            'test@example.com',
            'testpass@123',
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title='sample recipe name',
            time_minutes=5,
            price=Decimal('5.50'),
            description='simple recipe description',
        )
        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Tag1')

        self.assertEqual(str(tag), tag.name)
