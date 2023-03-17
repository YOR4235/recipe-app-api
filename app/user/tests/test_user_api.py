import email
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from yaml import StreamStartEvent

CREATE_USER_URL = reverse('user:create')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class publicUserAPITests(TestCase):

    def setUp(self):
        self.client = APIClient

    def test_create_user_success(self):
        payload = {
            'email': 'test@example.com',
            'password': 'testpass1234',
            'name': 'test name',
        }
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exist_error(self):
        payload = {
            'email': 'test@example.com',
            'password': 'testpass1234',
            'name': 'test name',
        }
        create_user(payload)
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_with_password_short(self):
        payload = {
            'email': 'test@example.com',
            'password': 'test',
            'name': 'test name',
        }
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exist = get_user_model().objects.filter(
            email=payload['email']).exists()
        self.assertFalse(user_exist)
